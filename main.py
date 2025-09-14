from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
from services.analytics import ClientAnalyzer

app = FastAPI()

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClientRequest(BaseModel):
    client_code: int


class Recommendation(BaseModel):
    product: str
    message: str
    confidence: float


class DiagnosticResponse(BaseModel):
    client_name: str
    recommendations: List[Recommendation]


# Хранилище созданных анализаторов и маппинг client_code -> analyzer
analyzers: List[ClientAnalyzer] = []
client_code_to_analyzer: Dict[int, ClientAnalyzer] = {}

# Инициализация анализаторов
for i in range(60):
    try:
        analyzer = ClientAnalyzer(
            f"data/client_{i+1}_transactions_3m.csv",
            f"data/client_{i+1}_transfers_3m.csv",
        )
        analyzers.append(analyzer)

        # Попробуем получить клиентов из данного анализатора (если метод get_all_clients есть)
        try:
            clients_part = analyzer.get_all_clients()
            if isinstance(clients_part, list):
                for c in clients_part:
                    cid = c.get("client_code")
                    if cid is not None:
                        # если несколько анализаторов возвращают один и тот же client_code,
                        # последний перезапишет, что обычно нормально (или можно сохранить список)
                        client_code_to_analyzer[cid] = analyzer
        except Exception:
            # Если analyzer не поддерживает get_all_clients или упал — пропускаем маппинг
            pass

    except Exception as e:
        print(f"Warning: failed to initialize analyzer for client {i+1}: {e}")
        continue


@app.get("/api/clients")
async def get_clients():
    """
    Возвращает агрегированный список клиентов (уникальные по client_code).
    """
    clients: List[Dict[str, Any]] = []
    seen_client_codes = set()

    # Если есть метод get_all_clients у анализаторов — соберём их
    for analyzer in analyzers:
        try:
            part = analyzer.get_all_clients()
            for c in part:
                cid = c.get("client_code")
                if cid is None:
                    continue
                if cid not in seen_client_codes:
                    seen_client_codes.add(cid)
                    clients.append(c)
        except Exception as e:
            print(f"Warning: failed to read clients from one analyzer: {e}")
            continue

    # Если не удалось получить через get_all_clients, можно заполнить из маппинга
    if not clients and client_code_to_analyzer:
        for cid in client_code_to_analyzer.keys():
            clients.append({"client_code": cid})

    if not clients:
        raise HTTPException(status_code=404, detail="Клиенты не найдены")

    return {"clients": clients}


@app.post("/api/diagnose", response_model=DiagnosticResponse)
async def diagnose_client(request: ClientRequest) -> DiagnosticResponse:
    """
    Запустить диагностику для одного клиента (по client_code).
    """
    try:
        # Небольшая имитация задержки для UX; не блокирует event loop.
        await asyncio.sleep(0.1)

        analyzer = client_code_to_analyzer.get(request.client_code)
        if analyzer is None:
            raise HTTPException(status_code=404, detail="Клиент не найден (analyzer не найден)")

        client_info = analyzer.analyze_client(request.client_code)
        if not client_info:
            raise HTTPException(status_code=404, detail="Клиент не найден (данные)")

        products = analyzer.calculate_product_scores(client_info)

        recommendations: List[Recommendation] = []
        for product, benefit, confidence in products[:3]:  # Топ-3 рекомендации
            message = analyzer.generate_notification(client_info, product, client_info.get("metrics", {}))
            recommendations.append(Recommendation(
                product=product,
                message=message,
                confidence=float(confidence)
            ))

        return DiagnosticResponse(
            client_name=client_info.get("name", f"client_{request.client_code}"),
            recommendations=recommendations
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diagnose_all")
async def diagnose_all():
    """
    Запустить диагностику для всех доступных клиентов (используя client_code_to_analyzer).
    Возвращает список результатов и ошибок.
    """
    results = []
    errors = []

    # Если у вас очень много клиентов и тяжелая обработка — подумайте об батчировании/фоновом исполнении.
    for client_code, analyzer in client_code_to_analyzer.items():
        try:
            client_info = analyzer.analyze_client(client_code)
            if not client_info:
                errors.append({"client_code": client_code, "error": "client data not found"})
                continue

            products = analyzer.calculate_product_scores(client_info)
            recs = []
            for product, benefit, confidence in products[:3]:
                message = analyzer.generate_notification(client_info, product, client_info.get("metrics", {}))
                recs.append({
                    "product": product,
                    "message": message,
                    "confidence": float(confidence)
                })

            results.append({
                "client_code": client_code,
                "client_name": client_info.get("name"),
                "recommendations": recs
            })

            # Небольшая пауза, чтобы не перегружать ресурсы (опционально)
            await asyncio.sleep(0.01)

        except Exception as e:
            errors.append({"client_code": client_code, "error": str(e)})
            continue

    return {"results": results, "errors": errors}


@app.get("/")
async def root():
    return {"message": "API для диагностики клиентов банка"}
