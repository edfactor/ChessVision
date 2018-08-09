from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
  
  local = False
  
  if local:
    endpoint = "http://localhost:7777/"
  else:
    endpoint = "http://23.97.186.93:8080/"

  return render_template('index.html', endpoint=endpoint)

if __name__ == '__main__':  
  app.run(host='127.0.0.1', port=5000)