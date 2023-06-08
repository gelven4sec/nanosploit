# nanoSploit

Minimalist C2 server for educational purpose.

## Features

### Principals

- Encrypted reverse shell
- Port scanner
- DNS ex-filtration
- Persistence

### Bonus

- Multi-session
- Upload/download files
- Cross-platform
- No external modules in payload (no need to `pip install` something)

## Usage

### Server

Run the program terminal :
```shell
python -m nanosploit
```

### Client

Run the program for debugging :
```shell
python -m nanosploit client
```

Export a payload to execute on victim :
```shell
python -m nanosploit generate --path payload.py --host 127.0.0.1 --port 5353
```
