# AI Font Generator

A monorepo for an AI-powered font generation web app. Deployable on Railway (backend) and Vercel (frontend).

---

## Project Structure

```
AI-font-full-repo/
├── backend/         # Python FastAPI backend
│   └── backend/     # Source code, requirements.txt
├── frontend/        # Next.js frontend app
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── public/
└── README.md
```

---

## Deployment

- **Backend:** Deploy to [Railway](https://railway.app/) (Dockerfile included)
- **Frontend:** Deploy to [Vercel](https://vercel.com/) (Next.js, zero-config)

---

## Environment Variables

### Backend (`backend/.env`)
| Variable            | Description                        |
|---------------------|------------------------------------|
| `OPENAI_API_KEY`    | OpenAI API key for font generation |
| `OPENROUTER_API_KEY`| Openrouter API key for Qwen VLM    |


### Frontend (`frontend/.env.local`)
| Variable                | Description                        |
|-------------------------|------------------------------------|
| `NEXT_PUBLIC_API_URL`   | URL of deployed backend API        |
| `NEXT_PUBLIC_STRIPE_KEY`| Stripe publishable key             |
| `STRIPE_SECRET_KEY`     | If you want to accept payments     |


---

## Local Development

### Backend (Python/FastAPI)
**Recommended: Use Docker**

```bash
cd backend
# Create a .env file with required variables (see table above)
docker build -t ai-font-backend .
docker run --env-file .env -p 8000:8000 ai-font-backend
```

**If you want to run without Docker:**  
You must install [potrace](http://potrace.sourceforge.net/) and [fontforge](https://fontforge.org/) on your system.

```bash
cd backend
# Create a .env file with required variables
# Create a virtual environment
RUN python3 -m venv /venv
source venv/bin/activate
pip install -r requirements.txt
# Make sure potrace and fontforge are installed and available in your PATH
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Next.js/Node.js)
```bash
cd frontend
pnpm install
# Create .env.local with required variables (see table above)
pnpm run dev
```


---

## Contributing
- Open issues or pull requests for improvements.

---

## License
[MIT](LICENSE) 