# Payment schedule API

Сервіс формує та оновлює графік платежів за кредитом за допомогою Django REST Framework.

## Запуск у Docker

1. **Зібрати образ та підняти сервіси** (з Redis для кешу/розширень, хоча додаток працює і без нього):
   ```bash
   docker-compose build
   docker-compose up
   ```
2. API стане доступним на `http://localhost:8000/api/`.

Якщо потрібен лише додаток без Redis, можна запустити його напряму:
```bash
docker build -t payment-schedule .
docker run --rm -p 8000:8000 payment-schedule
```

## Використання API

### Створити графік платежів
`POST /api/loans/`
```json
{
  "amount": 1000,
  "loan_start_date": "2025-11-30",  
  "number_of_payments": 4,
  "periodicity": "1m",              // 1d, 5d, 2w, 3m тощо
  "interest_rate": 10                // річна ставка 10%
}
```
Відповідь містить `loan_id` та `schedule` зі списком платежів (id, дата, тіло, відсотки).

### Зменшити тіло конкретного платежу
`POST /api/loans/{loan_id}/payments/{sequence}/reduce/`
```json
{
  "reduction": 50
}
```
`sequence` — порядковий номер платежу у графіку. Після зміни повертається оновлений графік із перерахованими відсотками поточного та наступних платежів.

## Налаштування

- База даних: SQLite за замовчуванням.
- Додаткові залежності вказані у `requirements.txt`.
