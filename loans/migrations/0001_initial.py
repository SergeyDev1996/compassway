from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Loan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('loan_start_date', models.DateField()),
                ('number_of_payments', models.PositiveIntegerField()),
                ('periodicity', models.CharField(max_length=10)),
                ('interest_rate', models.DecimalField(decimal_places=4, max_digits=5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence', models.PositiveIntegerField()),
                ('due_date', models.DateField()),
                ('principal', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('interest', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('loan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='loans.loan')),
            ],
            options={
                'ordering': ['sequence'],
                'unique_together': {('loan', 'sequence')},
            },
        ),
    ]
