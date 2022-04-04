# Elastio API built with Lumen Framework (By Laravel)

[![Build Status](https://travis-ci.org/laravel/lumen-framework.svg)](https://travis-ci.org/laravel/lumen-framework)
[![Total Downloads](https://img.shields.io/packagist/dt/laravel/framework)](https://packagist.org/packages/laravel/lumen-framework)
[![Latest Stable Version](https://img.shields.io/packagist/v/laravel/framework)](https://packagist.org/packages/laravel/lumen-framework)
[![License](https://img.shields.io/packagist/l/laravel/framework)](https://packagist.org/packages/laravel/lumen-framework)

Laravel Lumen is a stunningly fast PHP micro-framework for building web applications with expressive, elegant syntax. We believe development must be an enjoyable, creative experience to be truly fulfilling. Lumen attempts to take the pain out of development by easing common tasks used in the majority of web projects, such as routing, database abstraction, queueing, and caching.

## Official Documentation

Documentation for the framework can be found on the [Lumen website](https://lumen.laravel.com/docs).

## Contributing

Thank you for considering contributing to Lumen! The contribution guide can be found in the [Laravel documentation](https://laravel.com/docs/contributions).

## Security Vulnerabilities

If you discover a security vulnerability within Lumen, please send an e-mail to Taylor Otwell at taylor@laravel.com. All security vulnerabilities will be promptly addressed.

## License

The Lumen framework is open-sourced software licensed under the [MIT license](https://opensource.org/licenses/MIT).

---
# Elastio

## Setup

- Install elastio CLI to /home/ubuntu
- Setup AWS CLI credentials in both /home/ubuntu/.aws and /root/.aws
- Create the following folder: /var/www/iscan_temp and allow ubuntu.www-data to write.
- Update visuders

## Permissions

In order for the web server to talk to the Elastio CLI you must add elastio to the visudors file.

`www-data ALL=(ALL) NOPASSWD:ALL`

---

## EBS Volume Backup

Endpoint: api/ebs/new

Method: POST

Body: JSON

### Curl Example:

```
curl --location --request POST 'https://api.yourname.com/api/ebs/new' \
--header 'api-key: valid-api-key' \
--header 'Content-Type: application/json' \
--data-raw '{
    "volumeID": "vol-?????????????"
}'
```

### Example JSON Response: (Recovery Point returned)

```
{
    "meta": {
        "success": "rp-?????????????"
    }
}
```

## EBS Volume Restore

Endpoint: api/ebs/restore

Method: POST

Body: JSON

### Curl Example:

```
curl --location --request POST 'https://api.yourname.com/api/ebs/restore' \
--header 'api-key: valid-api-key' \
--header 'Content-Type: application/json' \
--data-raw '{
    "recoveryID": "rp-?????????????"
}'
```

### Example JSON Response:

```
{
    "meta": {
        "success": "success"
    }
}
```

---

## EC2 Instance Backup

Endpoint: api/ec2/new

Method: POST

Body: JSON

### Curl Example:

```
curl --location --request POST 'https://api.yourname.com/api/ec2/new' \
--header 'api-key: valid-api-key' \
--header 'Content-Type: application/json' \
--data-raw '{
    "instanceID": "i-?????????????"
}'
```

### Example JSON Response: (Recovery Point returned)

```
{
    "meta": {
        "success": "rp-?????????????"
    }
}
```

## EC2 Instance Restore

Endpoint: api/ec2/restore

Method: POST

Body: JSON

### Curl Example:

```
curl --location --request POST 'https://api.yourname.com/api/ec2/restore' \
--header 'api-key: valid-api-key' \
--header 'Content-Type: application/json' \
--data-raw '{
    "recoveryID": "rp-?????????????"
}'
```

### Example JSON Response:

```
{
    "meta": {
        "success": "success"
    }
}
```

---

## iScan using Recovery Point

> When using iscan on a recovery point the job will run in the background using dedicated resources in AWS. The target host will not be used for the scan.

Endpoint: api/iscan/rp

Method: POST

Body: JSON

### Curl Example:

```
curl --location --request POST 'https://api.yourname.com/api/iscan/rp' \
--header 'api-key: valid-api-key' \
--header 'Content-Type: application/json' \
--data-raw '{
    "recoveryID": "rp-?????????????"
}'
```

### Example JSON Response:

```
{
    "meta": {
        "success": "success"
    }
}
```

## iScan using single upload file

> When using iscan to scan a single file the API will upload the file to the target server, scan the file, report the status then delete the file.

> When using Lumen to upload the file you must also make sure php.ini is set up to accept files larger than 2 MB or php will return an exception.

Endpoint: api/iscan/file

Method: POST

Body: POST-DATA

### Example Curl:

```
curl --location --request POST 'https://api.yourname.com/api/iscan/file' \
--header 'api-key: valid-api-key' \
--form 'iscan_file=@"/your/local_machine/files/filename.tar"'
```

### Example JSON Response:

```
{
    "meta": {
        "success": {
            "malware": {
                "clean_files": 1,
                "corrupted_files": 0,
                "encrypted_files": 0,
                "incomplete_files": 0,
                "infected_files": 0,
                "suspicious_files": 0,
                "total_files": 1
            },
            "ransomware": {
                "suspicious_files": 0,
                "total_files": 1
            }
        }
    }
}
```
