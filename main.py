from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import time
from services.analytics import ClientAnalyzer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = ClientAnalyzer('data/client_1_transactions_3m.csv', 'data/client_1_transfers_3m.csv')


class ClientRequest(BaseModel):
    client_code: int


class Recommendation(BaseModel):
    product: str
    message: str
    confidence: float


class DiagnosticResponse(BaseModel):
    client_name: str
    recommendations: List[Recommendation]


an = []

for i in range(60):
    try:
        an.append(ClientAnalyzer(f'data/client_{i + 1}_transactions_3m.csv', f'data/client_{i + 1}_transfers_3m.csv'))
    except Exception as e:
        print(f"Warning: failed to initialize analyzer for client {i + 1}: {e}")
        continue


@app.get("/api/clients")
async def get_clients():
    clients: List[Dict] = []
    seen_client_codes = set()

    for analyzer in an:
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

            # В проде лучше использовать logger: logger.exception(...)
            print(f"Warning: failed to read clients from one analyzer: {e}")
            continue

    if not clients:
        # Если ни один analyzer не вернул клиентов — сообщаем об этом
        raise HTTPException(status_code=404, detail="Клиенты не найдены")

    return {"clients": clients}


@app.post("/api/diagnose")
async def diagnose_client(request: ClientRequest) -> DiagnosticResponse:
    """Запустить диагностику для клиента"""
    try:
        # Имитация времени обработки
        time.sleep(2)  # В реальности анализ быстрый, но для UX добавим задержку

        # Анализ клиента
        client_info = analyzer.analyze_client(request.client_code)

        if not client_info:
            raise HTTPException(status_code=404, detail="Клиент не найден")

        products = analyzer.calculate_product_scores(client_info)

        recommendations = []
        for product, benefit, confidence in products[:3]:  # Топ-3 рекомендации
            message = analyzer.generate_notification(client_info, product, client_info['metrics'])
            recommendations.append(Recommendation(
                product=product,
                message=message,
                confidence=confidence
            ))

        return DiagnosticResponse(
            client_name=client_info['name'],
            recommendations=recommendations
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "API для диагностики клиентов банка"}




