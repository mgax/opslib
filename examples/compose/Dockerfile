FROM python:slim
WORKDIR /app
RUN pip install Flask
COPY app.py ./
CMD flask run --host=0.0.0.0
