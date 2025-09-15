FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY social.org .
COPY org_social_preview_generator.py .
COPY template.html .

RUN mkdir -p /app/preview

CMD ["python", "org_social_preview_generator.py", "--social-file", "/app/social.org", "--preview-dir", "/app/preview", "--template-dir", "/app", "--template-name", "template.html"]
