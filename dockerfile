FROM python:3.12-alpine

ADD requirements.txt ronin.py skymavis.py main.py ./
ADD abis/ ./abis
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python", "main.py"]
