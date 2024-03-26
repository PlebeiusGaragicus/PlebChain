```sh
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```


```sh
chainlit create-secret | tail -n 1 >> .env

```