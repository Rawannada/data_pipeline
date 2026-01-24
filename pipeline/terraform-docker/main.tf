terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.1"
    }
  }
}

provider "docker" {}

# 1. سحب الصورة (Image)
resource "docker_image" "postgres_image" {
  name         = "postgres:13"
  keep_locally = true
}

# 2. تشغيل الحاوية (Container)
resource "docker_container" "postgres_db" {
  image = docker_image.postgres_image.image_id
  name  = "ny_taxi_db_from_terraform"
  
  env = [
    "POSTGRES_USER=root",
    "POSTGRES_PASSWORD=root",
    "POSTGRES_DB=ny_taxi"
  ]

  ports {
    internal = 5432
    external = 5433 # غيرناه لـ 5433 عشان ميتعارضش مع شغلك القديم
  }
}