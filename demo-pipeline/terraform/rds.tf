data "aws_rds_engine_version" "pg" {
  engine = "postgres"
}

resource "aws_security_group" "rds" {
  name        = "DBAccess"
  description = "Postgres RDS DB access"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = -1
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description     = "Allow inbound connections to postgres"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.elastio_instance.id]
  }
}

resource "aws_db_subnet_group" "rds_sg" {
  name       = "elastio-testing"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_db_instance" "test_instance" {
  identifier             = "elstio-demo"
  engine                 = "postgres"
  engine_version         = data.aws_rds_engine_version.pg.version
  instance_class         = "db.t3.micro"
  allocated_storage      = 10
  username               = "postgres"
  password               = "postgres"
  publicly_accessible    = false
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.rds_sg.name
  skip_final_snapshot    = true
}

