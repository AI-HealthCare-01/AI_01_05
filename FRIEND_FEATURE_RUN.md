# Friend Feature Run Guide (Copy Project)

## 1) Run server
```bash
cd /Users/admin/PyCharmProjects/AI_Health_final_copy
uv run uvicorn app.main_friend_feature:app --host 0.0.0.0 --port 8010 --reload
```

## 2) Open pages
- Friend pick: `http://localhost:8010/ui/friend/main`
- Friend check: `http://localhost:8010/ui/friend/check`
- Main screen: `http://localhost:8010/ui/main`

## 3) Mobile access
- Find local IP: `ipconfig getifaddr en0`
- Open: `http://<YOUR_IP>:8010/ui/friend/main`
