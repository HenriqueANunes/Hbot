from flask import Flask
from flask import cli
from threading import Thread


app = Flask('')

@app.route('/')
def home():
    return "Hello. I am alive!"

def run():

  cli.show_server_banner = lambda *_: None
  app.run(host='0.0.0.0',port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()