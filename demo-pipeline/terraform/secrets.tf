locals {
  db_secrets = {
    hostname = split(":", aws_db_instance.test_instance.endpoint)[0]
    port     = split(":", aws_db_instance.test_instance.endpoint)[1]
    username = aws_db_instance.test_instance.username
    password = aws_db_instance.test_instance.password
    database = aws_db_instance.test_instance.db_name
  }
}

resource "aws_secretsmanager_secret" "db" {
  name        = "demoapp/database/demo/credentials"
  description = "Database credentials for the elastio demo"
}

resource "aws_secretsmanager_secret_version" "shhh" {
  secret_id     = aws_secretsmanager_secret.db.id
  secret_string = jsonencode(local.db_secrets)
}
