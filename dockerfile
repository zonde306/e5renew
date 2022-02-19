FROM python:3
WORKDIR /usr/src/e5renew
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 25009
CMD [ "uvicorn", "main:app", "--host=0.0.0.0", "--port=25009", "--reload" ]
