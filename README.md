# nanoSploit

Minimalist C2 server for educational purpose.

## Usage

### Server

Generate a SSL certificate :
```shell
openssl req -newkey rsa:2048 -nodes -keyout ns_key.pem -x509 -days 365 -out ns_cert.pem -subj "/C=XX/ST=StateName/L=CityName/O=CompanyName/OU=CompanySectionName/CN=CommonNameOrHostname"
```

Run the program :
```shell
python -m nanosploit
```

### Client

Run the program :
```shell
python -m nanosploit client
```