from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="user", name="active_workspace",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="active_users", to="core.workspace"),
        ),
        migrations.CreateModel(
            name="Attachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("file", models.FileField(upload_to="tenant-attachments/%Y/%m/")),
                ("original_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=120)),
                ("size", models.PositiveBigIntegerField(default=0)),
                ("issue", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attachments", to="core.issue")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="core.user")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.workspace")),
            ],
        ),
    ]
