import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime
import csv
import os


class ClientAnalyzer:
    def __init__(self, transactions_path: str, transfers_path: str):
        self.transactions_df = pd.read_csv(transactions_path)
        self.transfers_df = pd.read_csv(transfers_path)

        # Преобразование дат
        self.transactions_df['date'] = pd.to_datetime(self.transactions_df['date'])
        self.transfers_df['date'] = pd.to_datetime(self.transfers_df['date'])

    def get_all_clients(self) -> List[Dict]:
        """Получить список всех клиентов"""
        clients = self.transactions_df.groupby('client_code').first().reset_index()
        return clients[['client_code', 'name', 'product', 'status', 'city']].to_dict('records')

    def analyze_client(self, client_code: int) -> Dict:
        """Анализ данных одного клиента"""
        client_trans = self.transactions_df[self.transactions_df['client_code'] == client_code].copy()
        client_transfers = self.transfers_df[self.transfers_df['client_code'] == client_code].copy()

        if client_trans.empty:
            return None

        # Базовая информация
        client_info = {
            'client_code': client_code,
            'name': client_trans['name'].iloc[0],
            'status': client_trans['status'].iloc[0],
            'city': client_trans['city'].iloc[0],
        }

        # Анализ транзакций
        category_spending = client_trans.groupby('category')['amount'].agg(['sum', 'count']).round(2)
        category_spending = category_spending.sort_values('sum', ascending=False)

        # Анализ переводов
        transfers_in = client_transfers[client_transfers['direction'] == 'in']
        transfers_out = client_transfers[client_transfers['direction'] == 'out']

        total_in = transfers_in['amount'].sum() if not transfers_in.empty else 0
        total_out = transfers_out['amount'].sum() if not transfers_out.empty else 0
        avg_monthly_balance = (total_in - total_out) / 3

        # Метрики
        metrics = {
            'total_spending': float(client_trans['amount'].sum()),
            'travel_spending': float(
                client_trans[client_trans['category'].isin(['Путешествия', 'Отели', 'Такси'])]['amount'].sum()),
            'restaurant_spending': float(client_trans[client_trans['category'] == 'Кафе и рестораны']['amount'].sum()),
            'online_spending': float(
                client_trans[client_trans['category'].isin(['Едим дома', 'Смотрим дома', 'Играем дома'])][
                    'amount'].sum()),
            'luxury_spending': float(
                client_trans[client_trans['category'].isin(['Ювелирные украшения', 'Косметика и Парфюмерия'])][
                    'amount'].sum()),
            'has_fx': bool(
                transfers_out['type'].isin(['fx_buy', 'fx_sell']).any()) if not transfers_out.empty else False,
            'has_gold': bool(transfers_out['type'].isin(
                ['gold_buy_out', 'gold_sell_in']).any()) if not transfers_out.empty else False,
            'has_investments': bool(
                transfers_out['type'].isin(['invest_out', 'invest_in']).any()) if not transfers_out.empty else False,
            'atm_withdrawals': float(transfers_out[transfers_out['type'] == 'atm_withdrawal'][
                                         'amount'].sum()) if not transfers_out.empty else 0,
            'avg_monthly_balance': float(avg_monthly_balance),
            'top_categories': category_spending.head(3).index.tolist()
        }

        client_info['metrics'] = metrics
        return client_info

    def calculate_product_scores(self, client_info: Dict) -> List[Tuple[str, float, float]]:
        """Расчет выгоды и уверенности для каждого продукта"""
        metrics = client_info['metrics']
        products = []

        # 1. Карта для путешествий
        travel_benefit = metrics['travel_spending'] * 0.04
        travel_confidence = min(95, 50 + (metrics['travel_spending'] / metrics['total_spending'] * 100) if metrics[
                                                                                                               'total_spending'] > 0 else 0)
        if travel_benefit > 1000:
            products.append(('Карта для путешествий', travel_benefit, travel_confidence))

        # 2. Премиальная карта
        premium_benefit = metrics['total_spending'] * 0.02
        premium_benefit += metrics['restaurant_spending'] * 0.02
        premium_benefit += metrics['luxury_spending'] * 0.02
        premium_confidence = min(92, 60 + (metrics['avg_monthly_balance'] / 500000 * 30) if metrics[
                                                                                                'avg_monthly_balance'] > 0 else 60)
        if metrics['avg_monthly_balance'] > 500000:
            premium_benefit *= 1.5
            products.append(('Премиальная карта', premium_benefit, premium_confidence))

        # 3. Кредитная карта
        credit_benefit = metrics['online_spending'] * 0.10
        top_spending = sum([metrics.get(f'{cat.lower()}_spending', 0) for cat in metrics['top_categories'][:3]])
        credit_benefit += top_spending * 0.10
        credit_confidence = min(88, 70 + (metrics['online_spending'] / metrics['total_spending'] * 50) if metrics[
                                                                                                              'total_spending'] > 0 else 70)
        if credit_benefit > 2000:
            products.append(('Кредитная карта', credit_benefit, credit_confidence))

        # 4. Обмен валют
        if metrics['has_fx']:
            fx_confidence = 85
            products.append(('Обмен валют', 50000, fx_confidence))

        # 5. Депозиты
        if metrics['avg_monthly_balance'] > 100000:
            deposit_benefit = metrics['avg_monthly_balance'] * 0.15 / 12 * 3
            if metrics['avg_monthly_balance'] > 1000000:
                products.append(('Депозит сберегательный', deposit_benefit * 1.2, 90))
            else:
                products.append(('Депозит накопительный', deposit_benefit, 85))

        # 6. Инвестиции
        if metrics['has_investments'] or metrics['avg_monthly_balance'] > 500000:
            invest_benefit = metrics['avg_monthly_balance'] * 0.20 / 12 * 3
            products.append(('Инвестиции', invest_benefit, 82))

        # 7. Золотые слитки
        if metrics['has_gold']:
            products.append(('Золотые слитки', 100000, 95))

        # Сортировка по выгоде
        products.sort(key=lambda x: x[1], reverse=True)
        return products[:4]  # Топ-4 продукта

    def generate_notification(self, client_info: Dict, product: str, metrics: Dict) -> str:
        """Генерация персонализированного уведомления"""
        name = client_info['name']

        templates = {
            'Карта для путешествий': f"{name}, в последние месяцы у вас много расходов на поездки и такси ({metrics['travel_spending']:.0f} ₸). С картой для путешествий вернули бы {metrics['travel_spending'] * 0.04:.0f} ₸ кешбэка. Оформить карту.",

            'Премиальная карта': f"{name}, у вас стабильный остаток на счету и активные траты. Премиальная карта даст до 4% кешбэка и бесплатные снятия. Подключить сейчас.",

            'Кредитная карта': f"{name}, ваши топ-категории — {', '.join(metrics['top_categories'][:2])}. Кредитная карта даёт до 10% в любимых категориях. Оформить карту.",

            'Обмен валют': f"{name}, вы совершаете валютные операции. В приложении выгодный обмен без скрытых комиссий. Настроить обмен.",

            'Депозит накопительный': f"{name}, у вас остаются свободные средства. Разместите их на вкладе — получайте до 15% годовых. Открыть вклад.",

            'Депозит сберегательный': f"{name}, ваш высокий остаток может работать. Сберегательный депозит даст максимальную ставку. Открыть вклад.",

            'Инвестиции': f"{name}, попробуйте инвестиции с низким порогом входа. Начните с малого. Открыть счёт.",

            'Золотые слитки': f"{name}, вы уже инвестируете в золото. Расширьте портфель с выгодными условиями. Узнать больше.",

            'Кредит наличными': f"{name}, нужны средства на крупные покупки? Кредит с гибкими условиями. Узнать лимит."
        }

        notification = templates.get(product, f"{name}, откройте новые возможности с {product}. Узнать больше.")

        if len(notification) > 220:
            notification = notification[:217] + "..."

        return notification


def generate_recommendations_csv(output_file: str = "client_recommendations.csv"):
    """
    Генерирует CSV файл с рекомендациями для всех клиентов
    """

    # Хранилище результатов
    recommendations = []

    # Инициализация анализаторов для всех 60 клиентов
    for i in range(60):
        try:
            transactions_file = f"data/client_{i + 1}_transactions_3m.csv"
            transfers_file = f"data/client_{i + 1}_transfers_3m.csv"

            # Проверяем существование файлов
            if not os.path.exists(transactions_file) or not os.path.exists(transfers_file):
                print(f"Warning: Files for client {i + 1} not found, skipping...")
                continue

            # Создаем анализатор
            analyzer = ClientAnalyzer(transactions_file, transfers_file)

            # Получаем всех клиентов из этого файла
            clients = analyzer.get_all_clients()

            for client in clients:
                client_code = client['client_code']

                try:
                    # Анализируем клиента
                    client_info = analyzer.analyze_client(client_code)
                    if not client_info:
                        continue

                    # Получаем топ рекомендации
                    products = analyzer.calculate_product_scores(client_info)

                    if products:  # Если есть хотя бы одна рекомендация
                        # Берем лучшую рекомендацию
                        best_product, benefit, confidence = products[0]

                        # Генерируем персонализированное уведомление
                        notification = analyzer.generate_notification(
                            client_info,
                            best_product,
                            client_info['metrics']
                        )

                        # Добавляем в результаты
                        recommendations.append({
                            'client_code': client_code,
                            'product': best_product,
                            'push_notification': notification
                        })

                        print(f"Processed client {client_code}: {best_product}")

                except Exception as e:
                    print(f"Error processing client {client_code}: {e}")
                    continue

        except Exception as e:
            print(f"Error initializing analyzer for client {i + 1}: {e}")
            continue

    # Записываем результаты в CSV
    if recommendations:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['client_code', 'product', 'push_notification']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for rec in recommendations:
                writer.writerow(rec)

        print(f"\nСуccessfully generated {output_file} with {len(recommendations)} recommendations")

        # Показываем статистику по продуктам
        product_stats = {}
        for rec in recommendations:
            product = rec['product']
            product_stats[product] = product_stats.get(product, 0) + 1

        print("\nProduct recommendations statistics:")
        for product, count in sorted(product_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {product}: {count}")

    else:
        print("No recommendations generated!")


def main():
    """
    Основная функция для запуска генерации CSV
    """
    print("Starting CSV generation for client recommendations...")
    print("This process will analyze all available client data and generate recommendations.")
    print("-" * 70)

    # Генерируем CSV файл
    generate_recommendations_csv("client_recommendations.csv")

    print("-" * 70)
    print("Process completed!")


if __name__ == "__main__":
    main()