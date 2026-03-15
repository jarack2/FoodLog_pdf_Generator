from flask import Flask
from flask import request

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World!'


def generatePdf():
    return "generated"

@app.route('/generate', methods=['POST'])
def generate():
    if request.method == 'POST':
        # file = request.files['file']
        # print(file.name)
        return generatePdf()
    return "not implemented yet"


if __name__ == '__main__':
    app.run(debug=True)