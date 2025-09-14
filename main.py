from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import time
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

# Инициализация анализатора
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


@app.get("/api/clients")
async def get_clients():
    """Получить список всех клиентов"""
    try:
        clients = analyzer.get_all_clients()
        
        return {"clients": clients}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/clients/{")
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

        # Расчет продуктов
        products = analyzer.calculate_product_scores(client_info)

        # Генерация рекомендаций
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




