FROM itsafeaturemythic/mythic_python_base:latest as builder

COPY [".docker/requirements.txt", "requirements.txt"]
RUN python3 -m pip wheel --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim-bullseye

# Mono: 6.12
RUN apt-get update && apt-get install --no-install-recommends gnupg -y

COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

WORKDIR /Mythic/

COPY [".", "."]

CMD ["python3", "main.py"]