from enum import StrEnum
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from tortoise.queryset import QuerySet

from app.apis.v1.friend_feature_main_screen import router as main_screen_router
from app.core import config
from app.models.friend_models import (
    CharacterId,
    FriendCharacter,
    FriendUser,
    bootstrap_friend_data,
    ensure_friend_user,
    initialize_friend_tortoise,
)

app = FastAPI(title="Friend Character API (Sample)")
app.include_router(main_screen_router)
initialize_friend_tortoise(app, generate_schemas=True)


class Character(StrEnum):
    CHAMKKAE = "참깨"
    DEULKKAE = "들깨"
    TONGKKAE = "통깨"
    HEUKKKAE = "흑깨"


class CharacterInfoResponse(BaseModel):
    id: Character
    name: str
    description: str
    image_url: str | None = None


class CharacterSelectionResponse(BaseModel):
    selected_character: Character | None = None


class CharacterSelectRequest(BaseModel):
    character_id: Character


class DebugDbStatusResponse(BaseModel):
    db_path: str
    characters_count: int
    users_count: int
    selected_character_counts: dict[str, int]


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHARACTER_IMAGE_DIR = PROJECT_ROOT / "character_images"
FONT_FILE = PROJECT_ROOT / "MemomentKkukkukk.otf"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def get_character_image_url(file_name: str | None) -> str | None:
    if not file_name or not CHARACTER_IMAGE_DIR.exists():
        return None
    image_file = CHARACTER_IMAGE_DIR / file_name
    if image_file.exists() and image_file.suffix.lower() in IMAGE_EXTENSIONS:
        return f"/static/characters/{file_name}"
    return None


if CHARACTER_IMAGE_DIR.exists():
    app.mount("/static/characters", StaticFiles(directory=str(CHARACTER_IMAGE_DIR)), name="character_images")


@app.on_event("startup")
async def on_startup() -> None:
    await bootstrap_friend_data()
    await ensure_friend_user(1)


async def get_request_user(x_user_id: Annotated[int | None, Header()] = None) -> FriendUser:
    user_id = x_user_id or 1
    return await ensure_friend_user(user_id)


@app.get("/api/v1/users/characters", response_model=list[CharacterInfoResponse])
async def get_character_catalog() -> list[CharacterInfoResponse]:
    rows: QuerySet[FriendCharacter] = FriendCharacter.all().order_by("display_order")
    result = await rows
    return [
        CharacterInfoResponse(
            id=Character(row.id),
            name=row.name,
            description=row.description,
            image_url=get_character_image_url(row.image_file),
        )
        for row in result
    ]


@app.get("/api/v1/users/characters/{character_id}", response_model=CharacterInfoResponse)
async def get_character_detail(character_id: Character) -> CharacterInfoResponse:
    row = await FriendCharacter.get_or_none(id=character_id.value)
    if row is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return CharacterInfoResponse(
        id=Character(row.id),
        name=row.name,
        description=row.description,
        image_url=get_character_image_url(row.image_file),
    )


@app.get("/api/v1/users/me/character", response_model=CharacterSelectionResponse)
async def get_my_character(user: Annotated[FriendUser, Depends(get_request_user)]) -> CharacterSelectionResponse:
    selected = Character(user.selected_character_id) if user.selected_character_id else None
    return CharacterSelectionResponse(selected_character=selected)


@app.put("/api/v1/users/me/character", response_model=CharacterSelectionResponse)
async def select_my_character(
    request: CharacterSelectRequest,
    user: Annotated[FriendUser, Depends(get_request_user)],
) -> CharacterSelectionResponse:
    selected = await FriendCharacter.get_or_none(id=request.character_id.value)
    if selected is None:
        raise HTTPException(status_code=404, detail="Character not found")
    user.selected_character = selected
    await user.save(update_fields=["selected_character_id", "updated_at"])
    return CharacterSelectionResponse(selected_character=request.character_id)


@app.get("/api/v1/debug/db", response_model=DebugDbStatusResponse)
async def get_debug_db_status() -> DebugDbStatusResponse:
    characters_count = await FriendCharacter.all().count()
    users_count = await FriendUser.all().count()
    rows = await FriendUser.all().values("selected_character_id")

    selected_counts = {character.value: 0 for character in CharacterId}
    selected_counts["미선택"] = 0
    for row in rows:
        key = row["selected_character_id"] or "미선택"
        selected_counts[key] = selected_counts.get(key, 0) + 1

    return DebugDbStatusResponse(
        db_path=f"mysql://{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}",
        characters_count=characters_count,
        users_count=users_count,
        selected_character_counts=selected_counts,
    )


@app.get("/assets/fonts/MemomentKkukkukk.otf")
async def serve_custom_font() -> FileResponse:
    if not FONT_FILE.exists():
        raise HTTPException(status_code=404, detail="Font file not found")
    return FileResponse(
        path=str(FONT_FILE),
        media_type="font/otf",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@app.get("/ui/friend/check", response_class=HTMLResponse)
async def selected_friend_ui() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <link rel="preload" href="/assets/fonts/MemomentKkukkukk.otf?v=20260301" as="font" type="font/otf" />
  <title>선택 확인</title>
  <style>
    @font-face {
      font-family: "MemomentKkukkukk";
      src: url("/assets/fonts/MemomentKkukkukk.otf?v=20260301") format("opentype"), local("MemomentKkukkukk");
      font-weight: 400;
      font-display: swap;
    }

    :root {
      --bg-solid: #f4efe2;
      --ink: #3f352a;
      --sub-ink: #7a6a58;
      --line: rgba(126, 108, 86, 0.22);
    }

    * { box-sizing: border-box; }

    body, body * {
      font-family: "MemomentKkukkukk", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    }
    button, input, textarea, select {
      font: inherit;
    }

    body {
      margin: 0;
      min-height: 100dvh;
      display: flex;
      flex-direction: column;
      font-family: "MemomentKkukkukk", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 20% 0%, rgba(255, 255, 255, 0.48), rgba(255, 255, 255, 0)),
        linear-gradient(180deg, #f8f3ea, var(--bg-solid));
    }

    .top-bar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 900;
      height: calc(env(safe-area-inset-top, 0px) + 72px);
      padding-top: env(safe-area-inset-top, 0px);
      background: linear-gradient(180deg, rgba(246, 236, 220, 0.94), rgba(238, 225, 205, 0.86));
      border-bottom: 1px solid rgba(179, 150, 121, 0.35);
      box-shadow: 0 6px 12px rgba(126, 98, 72, 0.12);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .top-logo {
      position: absolute;
      left: 14px;
      top: calc(env(safe-area-inset-top, 0px) + 8px);
      width: 56px;
      height: 56px;
      border-radius: 18px;
      border: 1px solid rgba(189, 154, 122, 0.35);
      background: linear-gradient(160deg, #fff8ec, #f3e2ca);
      box-shadow: 0 10px 22px rgba(132, 101, 72, 0.16);
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      color: #8b6541;
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.06em;
    }

    .top-bar-text {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 700;
      color: #5b4633;
      line-height: 1;
    }

    .wrap {
      max-width: 760px;
      margin: 0 auto;
      width: 100%;
      flex: 1;
      padding: calc(env(safe-area-inset-top, 0px) + 98px) 24px 40px;
    }

    .flow-surface {
      position: relative;
      background:
        repeating-linear-gradient(
          to bottom,
          rgba(255, 252, 245, 0.98) 0px,
          rgba(255, 252, 245, 0.98) 30px,
          rgba(197, 175, 150, 0.14) 31px
        );
      border: 1px solid rgba(188, 165, 140, 0.48);
      border-radius: 22px;
      padding: 18px 14px 16px 34px;
      box-shadow:
        0 12px 24px rgba(110, 90, 70, 0.16),
        inset 0 1px 0 rgba(255, 255, 255, 0.8);
      backdrop-filter: blur(6px);
    }

    .flow-surface::before {
      content: "";
      position: absolute;
      top: 10px;
      bottom: 10px;
      left: 20px;
      width: 2px;
      background: rgba(206, 124, 116, 0.36);
      border-radius: 2px;
      pointer-events: none;
    }

    .flow-surface::after {
      content: "";
      position: absolute;
      top: 24px;
      bottom: 24px;
      left: -9px;
      width: 14px;
      background:
        radial-gradient(circle, rgba(185, 161, 136, 0.75) 45%, rgba(185, 161, 136, 0) 48%)
        center top / 12px 44px repeat-y;
      pointer-events: none;
      opacity: 0.8;
    }

    .tape {
      position: absolute;
      width: 64px;
      height: 18px;
      top: -8px;
      background: rgba(246, 229, 161, 0.56);
      border: 1px dashed rgba(170, 141, 84, 0.3);
      box-shadow: 0 2px 5px rgba(91, 71, 38, 0.08);
      border-radius: 3px;
      pointer-events: none;
      backdrop-filter: blur(1px);
    }

    .tape.left {
      left: 36px;
      transform: rotate(-7deg);
    }

    .tape.right {
      right: 20px;
      transform: rotate(8deg);
    }

    .flow-divider {
      height: 1px;
      background: linear-gradient(90deg, rgba(121, 94, 67, 0), rgba(121, 94, 67, 0.34), rgba(121, 94, 67, 0));
      margin: 8px 0 10px;
    }

    .check-title {
      margin: 0;
      font-size: 1.24rem;
      color: #5a4432;
      text-align: center;
      letter-spacing: -0.01em;
    }

    .check-sub {
      margin: 6px 0 10px;
      text-align: center;
      color: #7f6b57;
      font-size: 0.9rem;
      line-height: 1.45;
    }

    .status {
      margin: 0;
      padding: 8px 10px;
      font-size: 0.95rem;
      color: #7d6149;
      text-align: center;
      min-height: 1.5em;
      border-radius: 11px;
      border: 1px solid rgba(172, 145, 119, 0.34);
      background: rgba(255, 250, 243, 0.86);
    }

    .status.tone-ok {
      color: #6f4b2f;
      border-color: rgba(160, 120, 82, 0.42);
      background: rgba(255, 247, 237, 0.9);
    }

    .status.tone-warn {
      color: #7f4f33;
      border-color: rgba(168, 108, 81, 0.42);
      background: rgba(255, 242, 233, 0.9);
    }

    .status.tone-neutral {
      color: #7d6149;
    }

    .friend-card {
      margin-top: 2px;
      border: 1px solid rgba(168, 141, 113, 0.3);
      border-radius: 16px;
      background: #fffdf8;
      overflow: hidden;
      box-shadow: 0 8px 16px rgba(20, 46, 52, 0.08);
      opacity: 0;
      transform: translateY(6px);
      transition: opacity 170ms ease, transform 170ms ease;
    }

    .friend-card.hidden {
      display: none;
    }

    .friend-card.show {
      opacity: 1;
      transform: translateY(0);
    }

    .friend-image-wrap {
      position: relative;
    }

    .friend-image {
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: cover;
      background: #eef1f1;
      border-bottom: 1px solid rgba(24, 53, 58, 0.12);
    }

    .friend-bubble {
      position: absolute;
      top: 10px;
      right: 10px;
      max-width: 74%;
      padding: 9px 11px;
      border-radius: 16px;
      border: 1px solid rgba(94, 141, 114, 0.35);
      background: linear-gradient(180deg, rgba(239, 253, 243, 0.96), rgba(227, 245, 233, 0.96));
      color: #2f6f4c;
      font-size: 0.9rem;
      font-weight: 700;
      line-height: 1.4;
      white-space: pre-line;
      word-break: keep-all;
      box-shadow: 0 8px 16px rgba(65, 128, 93, 0.18);
    }

    .friend-bubble::after {
      content: "";
      position: absolute;
      right: 12px;
      bottom: -7px;
      width: 11px;
      height: 11px;
      background: rgba(227, 245, 233, 0.96);
      border-right: 1px solid rgba(94, 141, 114, 0.35);
      border-bottom: 1px solid rgba(94, 141, 114, 0.35);
      transform: rotate(45deg);
    }

    .friend-body {
      padding: 12px 12px 14px;
      text-align: center;
    }

    .friend-name {
      margin: 0;
      font-size: 1.34rem;
      color: #5d4835;
    }

    .friend-desc {
      margin: 8px 0 0;
      font-size: 0.95rem;
      line-height: 1.5;
      color: var(--sub-ink);
    }

    .toggle-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-top: 12px;
      flex-wrap: wrap;
    }

    .text-toggle {
      margin: 0;
      padding: 4px 2px;
      flex: 1;
      width: 100%;
      font-size: 1rem;
      font-weight: 700;
      color: #6f5d49;
      border-bottom: 2px dashed rgba(145, 122, 98, 0.46);
      letter-spacing: 0.01em;
      user-select: none;
      cursor: default;
      opacity: 0.48;
      pointer-events: none;
      transition: transform 120ms ease, color 120ms ease, border-color 120ms ease, opacity 120ms ease;
    }

    .text-toggle.enabled {
      color: #9b4f2d;
      border-bottom-color: rgba(195, 104, 70, 0.72);
      opacity: 1;
      cursor: pointer;
      pointer-events: auto;
    }

    .text-toggle.enabled:active {
      transform: scale(0.985);
    }

    .text-toggle.prev {
      text-align: left;
    }

    .text-toggle.next {
      text-align: right;
    }

    .team-credit {
      width: max-content;
      margin: 0 auto calc(env(safe-area-inset-bottom, 0px) + 6px);
      padding: 0;
      border: 0;
      background: rgba(255, 235, 220, 0.86);
      color: rgba(96, 80, 64, 0.42);
      font-size: 0.62rem;
      letter-spacing: 0.01em;
      user-select: none;
      text-align: center;
    }

  </style>
</head>
<body>
  <header class="top-bar" aria-label="고정 상단 바">
    <div class="top-logo" aria-label="로고 영역">LOGO</div>
    <p class="top-bar-text">선택 확인</p>
  </header>

  <main class="wrap">
    <section class="flow-surface">
      <span class="tape left"></span>
      <span class="tape right"></span>
      <h1 class="check-title">친구 선택 확인 ♧</h1>
      <p class="check-sub">오늘부터 함께할 친구를<br />한 번 더 확인해볼까요?</p>
      <p id="status" class="status">선택한 친구 정보를 불러오는 중이에요...</p>
      <div class="flow-divider"></div>
      <article id="friendCard" class="friend-card hidden" aria-live="polite">
        <div class="friend-image-wrap">
          <img id="friendImage" class="friend-image" alt="선택한 친구 이미지" />
          <div id="friendBubble" class="friend-bubble"></div>
        </div>
        <div class="friend-body">
          <h1 id="friendName" class="friend-name"></h1>
          <p id="friendDesc" class="friend-desc"></p>
        </div>
      </article>
      <div class="toggle-row">
        <p id="backToggle" class="text-toggle prev enabled" role="button" tabindex="0" aria-disabled="false">← 친구 다시 고르기</p>
        <p id="startToggle" class="text-toggle next" role="button" tabindex="0" aria-disabled="true">확인 후 다음 →</p>
      </div>
    </section>
  </main>
  <div class="team-credit">Copyright 2026 5FCV. All rights reserved.</div>

  <script>
    const userId = "1";
    const pageParams = new URLSearchParams(window.location.search);
    const flowMode = pageParams.get("mode");
    const isSelectionFlow = flowMode === "first" || flowMode === "change";
    const tapeLayouts = [
      {
        left: { top: "-8px", right: "auto", bottom: "auto", left: "36px", width: "64px", height: "18px", transform: "rotate(-7deg)" },
        right: { top: "-8px", right: "20px", bottom: "auto", left: "auto", width: "64px", height: "18px", transform: "rotate(8deg)" }
      },
      {
        left: { top: "-6px", right: "auto", bottom: "auto", left: "34px", width: "64px", height: "18px", transform: "rotate(-11deg)" },
        right: { top: "30%", right: "-9px", bottom: "auto", left: "auto", width: "18px", height: "64px", transform: "rotate(7deg)" }
      },
      {
        left: { top: "-7px", right: "auto", bottom: "auto", left: "52px", width: "64px", height: "18px", transform: "rotate(-10deg)" },
        right: { top: "-8px", right: "18px", bottom: "auto", left: "auto", width: "64px", height: "18px", transform: "rotate(10deg)" }
      },
      {
        left: { top: "-9px", right: "auto", bottom: "auto", left: "45%", width: "64px", height: "18px", transform: "translateX(-50%) rotate(-3deg)" },
        right: { top: "38%", right: "-9px", bottom: "auto", left: "auto", width: "18px", height: "58px", transform: "rotate(6deg)" }
      },
      {
        left: { top: "-7px", right: "auto", bottom: "auto", left: "68px", width: "64px", height: "18px", transform: "rotate(-6deg)" },
        right: { top: "-7px", right: "26px", bottom: "auto", left: "auto", width: "64px", height: "18px", transform: "rotate(12deg)" }
      }
    ];
    const thankYouMessageTemplates = [
      (buddyName) => `${buddyName},\n나를 선택해줘서 고마워! 🍀`,
      (buddyName, nickname) => `${nickname} 덕분에\n내가 오늘 더 행복해 ♡`,
      (buddyName) => `${buddyName},\n같이 시작해줘서 정말 고마워 ☁️`,
      (buddyName) => `${buddyName}!\n내 편이 되어줘서 고마워 🐾`,
      (buddyName, nickname, nicknameWithAnd) => `${nicknameWithAnd} 함께라서 좋아!\n우리 잘 부탁해 ✨`,
      (buddyName) => `${buddyName},\n오늘 기록도 다정하게 도와줄게 📔`
    ];
    const characterThankYouMessageTemplates = {
      "참깨": [
        (buddyName) => `${buddyName},\n히히! 이제부터 내가\n웃음 담당할게 😜`,
        (buddyName) => `${buddyName} 선택 고마워!\n장난꾸러기 친구랑\n재밌게 가보자 🎈`,
        (buddyName) => `${buddyName},\n오늘은 내가 먼저\n장난 한 스푼 줄게 🤭`,
        (buddyName, nickname) => `${nickname} 덕분에\n내 꼬리가 살랑살랑해!\n신난다아 🐾`,
        (buddyName) => `${buddyName},\n심심할 틈 없게\n내가 깜짝 웃음 줄게 ✨`,
        (buddyName) => `${buddyName},\n우리 팀 이름은\n말랑 장난단이야! 🍬`
      ],
      "들깨": [
        (buddyName) => `${buddyName},\n나를 골라줘서 고마워.\n내가 다정히 챙겨줄게 🌿`,
        (buddyName) => `${buddyName},\n걱정되는 마음은\n내가 먼저 안아줄게 🤍`,
        (buddyName) => `${buddyName},\n오늘 컨디션도\n천천히 같이 살펴보자 ☁️`,
        (buddyName, nicknameWithAnd) => `${nicknameWithAnd} 함께면\n마음이 훨씬 든든해.\n내가 곁에 있을게 🌼`,
        (buddyName) => `${buddyName},\n무리하지 않게\n내가 속도 맞춰줄게 🍀`,
        (buddyName) => `${buddyName},\n힘든 마음은 잠깐 내려두고\n내 손 잡고 쉬어가자 🫶`
      ],
      "통깨": [
        (buddyName) => `${buddyName},\n우와 나를 골라줬네!\n완전 감동이야 ✨`,
        (buddyName) => `${buddyName},\n네 마음 하나하나\n내가 리액션 해줄게 💖`,
        (buddyName) => `${buddyName},\n와아~ 오늘 이야기\n내가 완전 공감해줄게 🌈`,
        (buddyName, nickname) => `${nickname} 기분 변화도\n내가 꼼꼼히 캐치할게!\n리액션 준비 완료 🙌`,
        (buddyName) => `${buddyName},\n토닥토닥 + 리액션 팡!\n내가 다 해줄게 🧸`,
        (buddyName) => `${buddyName},\n좋은 일도 힘든 일도\n같이 크게 공감하자 💫`
      ],
      "흑깨": [
        (buddyName) => `${buddyName},\n선택해줘서 고마워.\n이제 하나씩 알려줄게 📘`,
        (buddyName, nickname, nicknameWithAnd) => `${nicknameWithAnd} 함께\n차근차근 해보자.\n내가 옆에서 도와줄게 🫶`,
        (buddyName) => `${buddyName},\n먼저 쉬운 것부터\n순서대로 해보자 ✅`,
        (buddyName, nickname) => `${nickname} 페이스에 맞춰\n한 단계씩 안내할게.\n걱정하지 마 🌿`,
        (buddyName) => `${buddyName},\n헷갈리는 부분은\n내가 다시 천천히 설명할게 📎`,
        (buddyName) => `${buddyName},\n시작-중간-마무리까지\n내가 옆에서 챙길게 🤍`
      ]
    };

    function apiHeaders(extra = {}) {
      return { "X-User-Id": userId, ...extra };
    }

    function getCanonicalCharacterImageUrl(characterId, fallbackUrl = "") {
      const fixedMap = {
        "참깨": "/static/characters/chamkkae.jpeg",
        "들깨": "/static/characters/deulkkae.jpeg",
        "통깨": "/static/characters/tongkkae.jpeg",
        "흑깨": "/static/characters/heukkkae.jpeg"
      };
      const version = "friend-map-20260227";
      if (fixedMap[characterId]) return fixedMap[characterId] + "?v=" + version;
      if (fallbackUrl) return fallbackUrl + (fallbackUrl.includes("?") ? "&" : "?") + "v=" + version;
      return "";
    }

    function getFlowQuery() {
      if (flowMode === "change") return "?mode=change";
      if (flowMode === "first") return "?mode=first";
      return "";
    }

    function applyTapeStyle(el, style) {
      el.style.top = style.top;
      el.style.right = style.right;
      el.style.bottom = style.bottom;
      el.style.left = style.left;
      el.style.width = style.width;
      el.style.height = style.height;
      el.style.transform = style.transform;
    }

    function applyRandomTapeLayout() {
      const leftTape = document.querySelector(".tape.left");
      const rightTape = document.querySelector(".tape.right");
      if (!leftTape || !rightTape) return;
      const layout = tapeLayouts[Math.floor(Math.random() * tapeLayouts.length)];
      applyTapeStyle(leftTape, layout.left);
      applyTapeStyle(rightTape, layout.right);
    }

    async function getDisplayNickname() {
      try {
        const res = await fetch("/api/v1/main/me/profile", { headers: apiHeaders() });
        if (!res.ok) return "닉네임";
        const data = await res.json();
        const nickname = (data && data.nickname) ? String(data.nickname).trim() : "";
        return nickname || "닉네임";
      } catch (_error) {
        return "닉네임";
      }
    }

    function hasHangulBatchim(word) {
      const trimmed = (word || "").trim();
      if (!trimmed) return false;
      const lastChar = trimmed[trimmed.length - 1];
      const code = lastChar.charCodeAt(0) - 0xac00;
      if (code >= 0 && code <= 11171) {
        return code % 28 !== 0;
      }
      return false;
    }

    function getKoreanParticle(word, withBatchim, withoutBatchim) {
      return hasHangulBatchim(word) ? withBatchim : withoutBatchim;
    }

    function getNicknameVocative(nickname) {
      const trimmed = (nickname || "").trim();
      if (!trimmed) return "친구야";
      return trimmed + (hasHangulBatchim(trimmed) ? "아" : "야");
    }

    function getRandomThankYouMessage(nickname, characterId) {
      const characterTemplates = characterThankYouMessageTemplates[characterId] || [];
      const useCharacterTemplate =
        characterTemplates.length > 0 &&
        (thankYouMessageTemplates.length === 0 || Math.random() < 0.75);
      const pool = useCharacterTemplate ? characterTemplates : thankYouMessageTemplates;
      const template = pool[Math.floor(Math.random() * pool.length)];
      const baseNickname = (nickname || "").trim() || "친구";
      const buddyName = getNicknameVocative(baseNickname);
      const nicknameWithAnd = baseNickname + getKoreanParticle(baseNickname, "이와", "와");
      return template(buddyName, baseNickname, nicknameWithAnd);
    }

    async function loadSelectedFriend() {
      const statusEl = document.getElementById("status");
      const cardEl = document.getElementById("friendCard");
      const startToggle = document.getElementById("startToggle");
      const bubbleEl = document.getElementById("friendBubble");

      function setStatus(message, tone = "neutral") {
        statusEl.textContent = message;
        statusEl.classList.remove("tone-neutral", "tone-ok", "tone-warn");
        statusEl.classList.add("tone-" + tone);
      }

      function showCard() {
        cardEl.classList.remove("hidden");
        requestAnimationFrame(() => {
          cardEl.classList.add("show");
        });
      }

      function hideCard() {
        cardEl.classList.remove("show");
        cardEl.classList.add("hidden");
      }

      try {
        const myRes = await fetch("/api/v1/users/me/character", { headers: apiHeaders() });
        const my = await myRes.json();

        if (!my.selected_character) {
          window.location.replace("/ui/friend/main?mode=first");
          return;
        }

        if (!isSelectionFlow) {
          window.location.replace("/ui/main");
          return;
        }

        const detailRes = await fetch(
          "/api/v1/users/characters/" + encodeURIComponent(my.selected_character),
          { headers: apiHeaders() }
        );
        const detail = await detailRes.json();

        document.getElementById("friendImage").src = getCanonicalCharacterImageUrl(
          my.selected_character,
          detail.image_url || ""
        );
        const baseName = detail.name || my.selected_character;
        document.getElementById("friendName").textContent = baseName.endsWith("♧") ? baseName : (baseName + " ♧");
        document.getElementById("friendDesc").textContent = detail.description || "";
        const nickname = await getDisplayNickname();
        bubbleEl.textContent = getRandomThankYouMessage(nickname, my.selected_character);
        setStatus("선택이 완료되었어요. 이제 함께 시작해볼까요?", "ok");
        showCard();
        startToggle.classList.add("enabled");
        startToggle.setAttribute("aria-disabled", "false");
      } catch (error) {
        setStatus("정보를 불러오지 못했어요. 잠시 후 다시 시도해주세요.", "warn");
        hideCard();
        bubbleEl.textContent = "";
        startToggle.classList.remove("enabled");
        startToggle.setAttribute("aria-disabled", "true");
      }
    }

    function bindToggleAction(id, handler) {
      const el = document.getElementById(id);
      el.onclick = () => {
        if (el.getAttribute("aria-disabled") === "true") return;
        handler();
      };
      el.onkeydown = (event) => {
        if (el.getAttribute("aria-disabled") === "true") return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          handler();
        }
      };
    }

    bindToggleAction("backToggle", () => {
      window.location.href = "/ui/friend/main" + (getFlowQuery() || "?mode=change");
    });
    bindToggleAction("startToggle", () => {
      window.location.href = "/ui/main";
    });

    applyRandomTapeLayout();
    loadSelectedFriend();
  </script>
</body>
</html>
        """
    )


@app.get("/ui/friend/main", response_class=HTMLResponse)
async def character_select_ui() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <link rel="preload" href="/assets/fonts/MemomentKkukkukk.otf?v=20260301" as="font" type="font/otf" />
  <title>친구 선택</title>
  <style>
    @font-face {
      font-family: "MemomentKkukkukk";
      src: url("/assets/fonts/MemomentKkukkukk.otf?v=20260301") format("opentype"), local("MemomentKkukkukk");
      font-weight: 400;
      font-display: swap;
    }

    :root {
      --bg-solid: #f4efe2;
      --ink: #3f352a;
      --sub-ink: #7a6a58;
      --card: rgba(255, 252, 245, 0.95);
      --line: rgba(126, 108, 86, 0.22);
      --accent: #c96a42;
      --accent-soft: #f6dfd2;
      --overlay: rgba(40, 30, 20, 0.4);
    }

    * { box-sizing: border-box; }

    body, body * {
      font-family: "MemomentKkukkukk", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    }
    button, input, textarea, select {
      font: inherit;
    }

    body {
      margin: 0;
      min-height: 100dvh;
      display: flex;
      flex-direction: column;
      font-family: "MemomentKkukkukk", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 20% 0%, rgba(255, 255, 255, 0.48), rgba(255, 255, 255, 0)),
        linear-gradient(180deg, #f8f3ea, var(--bg-solid));
    }

    .wrap {
      max-width: 760px;
      margin: 0 auto;
      width: 100%;
      flex: 1;
      padding: calc(env(safe-area-inset-top, 0px) + 98px) 24px 40px;
    }

    .flow-surface {
      position: relative;
      background:
        repeating-linear-gradient(
          to bottom,
          rgba(255, 252, 245, 0.98) 0px,
          rgba(255, 252, 245, 0.98) 30px,
          rgba(197, 175, 150, 0.14) 31px
        );
      border: 1px solid rgba(188, 165, 140, 0.48);
      border-radius: 22px;
      padding: 18px 14px 16px 34px;
      box-shadow:
        0 12px 24px rgba(110, 90, 70, 0.16),
        inset 0 1px 0 rgba(255, 255, 255, 0.8);
      backdrop-filter: blur(6px);
    }

    .flow-surface::before {
      content: "";
      position: absolute;
      top: 10px;
      bottom: 10px;
      left: 20px;
      width: 2px;
      background: rgba(206, 124, 116, 0.36);
      border-radius: 2px;
      pointer-events: none;
    }

    .flow-surface::after {
      content: "";
      position: absolute;
      top: 24px;
      bottom: 24px;
      left: -9px;
      width: 14px;
      background:
        radial-gradient(circle, rgba(185, 161, 136, 0.75) 45%, rgba(185, 161, 136, 0) 48%)
        center top / 12px 44px repeat-y;
      pointer-events: none;
      opacity: 0.8;
    }

    .tape {
      position: absolute;
      width: 64px;
      height: 18px;
      top: -8px;
      background: rgba(246, 229, 161, 0.56);
      border: 1px dashed rgba(170, 141, 84, 0.3);
      box-shadow: 0 2px 5px rgba(91, 71, 38, 0.08);
      border-radius: 3px;
      pointer-events: none;
      backdrop-filter: blur(1px);
    }

    .tape.left {
      left: 36px;
      transform: rotate(-7deg);
    }

    .tape.right {
      right: 20px;
      transform: rotate(8deg);
    }

    .flow-divider {
      height: 1px;
      background: linear-gradient(90deg, rgba(121, 94, 67, 0), rgba(121, 94, 67, 0.34), rgba(121, 94, 67, 0));
      margin: 2px 0 10px;
    }

    .top-bar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 900;
      height: calc(env(safe-area-inset-top, 0px) + 72px);
      padding-top: env(safe-area-inset-top, 0px);
      background: linear-gradient(180deg, rgba(246, 236, 220, 0.94), rgba(238, 225, 205, 0.86));
      border-bottom: 1px solid rgba(179, 150, 121, 0.35);
      box-shadow: 0 6px 12px rgba(126, 98, 72, 0.12);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .top-logo {
      position: absolute;
      left: 14px;
      top: calc(env(safe-area-inset-top, 0px) + 8px);
      width: 56px;
      height: 56px;
      border-radius: 18px;
      border: 1px solid rgba(189, 154, 122, 0.35);
      background: linear-gradient(160deg, #fff8ec, #f3e2ca);
      box-shadow: 0 10px 22px rgba(132, 101, 72, 0.16);
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }

    .top-bar-text {
      margin: 0;
      font-size: 1.02rem;
      font-weight: 700;
      color: #5b4633;
      letter-spacing: -0.01em;
      line-height: 1;
    }

    .logo-placeholder {
      font-size: 0.7rem;
      font-weight: 800;
      color: #8b6541;
      letter-spacing: 0.06em;
    }

    .logo-image {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: none;
    }

    .hero {
      padding: 6px 4px 10px;
    }

    .hero h1 {
      margin: 0;
      font-family: "MemomentKkukkukk", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
      font-size: 1.45rem;
      line-height: 1.35;
      letter-spacing: -0.01em;
      text-wrap: balance;
      color: #5f4632;
    }

    .hero p {
      margin: 10px 0 0;
      color: var(--sub-ink);
      font-size: 0.95rem;
      line-height: 1.5;
    }

    .flow-surface,
    .flow-surface p,
    .flow-surface h2,
    .flow-surface span,
    .flow-surface button,
    .modal-title,
    .modal-desc,
    .ghost-btn,
    .pick-btn {
      font-family: "MemomentKkukkukk", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    }

    .status {
      margin: 12px 0 0;
      color: #9c5d34;
      font-weight: 700;
      min-height: 1.4em;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 9px;
    }

    .card-btn {
      border: 0;
      padding: 0;
      background: transparent;
      text-align: left;
      width: 100%;
    }

    .card {
      border: 1px solid var(--line);
      background: var(--card);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 8px 16px rgba(20, 46, 52, 0.08);
      transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
      position: relative;
    }

    .card-btn:nth-child(odd) .card {
      transform: rotate(-1deg);
    }

    .card-btn:nth-child(even) .card {
      transform: rotate(1deg);
    }

    .card.selected {
      border-color: #ff5a3c;
      box-shadow:
        0 0 0 2px rgba(255, 117, 77, 0.34),
        0 18px 34px rgba(255, 90, 60, 0.34);
      background: linear-gradient(180deg, rgba(255, 239, 228, 0.98), rgba(255, 250, 244, 0.98));
      transform: rotate(0deg) translateY(-1px) !important;
    }

    .stamp {
      position: absolute;
      bottom: 26px;
      right: 8px;
      z-index: 3;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 0.98rem;
      font-weight: 800;
      letter-spacing: 0.02em;
      color: rgba(132, 38, 18, 0.98);
      background: rgba(255, 245, 236, 0.52);
      border: 2px solid rgba(198, 48, 12, 0.95);
      box-shadow: 0 6px 12px rgba(149, 53, 23, 0.22);
      transform: rotate(8deg) scale(0.8);
      opacity: 0;
      pointer-events: none;
      mix-blend-mode: normal;
      backdrop-filter: blur(1px);
      -webkit-backdrop-filter: blur(1px);
    }

    .stamp::before {
      content: "";
      position: absolute;
      inset: 2px;
      border-radius: 999px;
      border: 1px dashed rgba(198, 48, 12, 0.86);
      pointer-events: none;
    }

    .card.selected .stamp {
      opacity: 1;
      animation: stamp-pop 240ms ease-out;
    }

    .photo-wrap {
      position: relative;
      padding: 8px 8px 0;
    }

    .pin {
      position: absolute;
      width: 13px;
      height: 13px;
      border-radius: 50%;
      background: radial-gradient(circle at 32% 30%, var(--pin-hi, #fff2f2) 0%, var(--pin-mid, #ff7f7f) 48%, var(--pin-edge, #bd3f3f) 100%);
      border: 1px solid rgba(79, 62, 62, 0.34);
      box-shadow: 0 1px 2px rgba(47, 54, 59, 0.26);
      z-index: 3;
      pointer-events: none;
    }

    .pin::after {
      content: "";
      position: absolute;
      left: 50%;
      top: 10px;
      width: 2px;
      height: 10px;
      border-radius: 1px;
      background: linear-gradient(180deg, rgba(170, 177, 182, 0.96), rgba(116, 124, 131, 0.96));
      transform: translateX(-50%);
    }

    .pin.c1 { --pin-hi: #ffe8e8; --pin-mid: #ff7a7a; --pin-edge: #bb3d3d; }
    .pin.c2 { --pin-hi: #e6f0ff; --pin-mid: #7ea9ff; --pin-edge: #3f67bf; }
    .pin.c3 { --pin-hi: #fff6db; --pin-mid: #ffd55d; --pin-edge: #bf8d22; }
    .pin.c4 { --pin-hi: #e5ffe9; --pin-mid: #7fdc90; --pin-edge: #3f9b56; }
    .pin.p1 { top: 3px; left: 12px; transform: rotate(-12deg); }
    .pin.p2 { top: 2px; left: 22px; transform: rotate(-4deg); }
    .pin.p3 { top: 3px; right: 14px; transform: rotate(10deg); }
    .pin.p4 { top: 2px; right: 22px; transform: rotate(6deg); }
    .pin.p5 { top: 1px; left: 48%; transform: translateX(-50%) rotate(-2deg); }
    .pin.p6 { top: 2px; left: 38%; transform: translateX(-50%) rotate(8deg); }

    .thumb {
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: cover;
      background: linear-gradient(180deg, #eef2f2, #e6ebeb);
      border-bottom: 1px solid rgba(24, 53, 58, 0.12);
      border-radius: 10px;
    }

    .label-row {
      padding: 8px 9px;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 6px;
    }

    .name {
      margin: 0;
      font-size: 1.12rem;
      font-weight: 700;
      color: #5d4835;
      letter-spacing: -0.02em;
      text-align: center;
    }

    .hint {
      font-size: 0.78rem;
      color: var(--sub-ink);
      margin: 8px 2px 0;
    }

    .next-wrap {
      margin-top: 12px;
      display: flex;
      justify-content: flex-end;
    }

    .next-toggle {
      margin: 0;
      padding: 4px 2px;
      font-size: 1.04rem;
      font-weight: 700;
      color: #6f5d49;
      border-bottom: 2px dashed rgba(145, 122, 98, 0.46);
      letter-spacing: 0.01em;
      user-select: none;
      cursor: default;
      opacity: 0.48;
      pointer-events: none;
      transition: transform 120ms ease, color 120ms ease, border-color 120ms ease, opacity 120ms ease;
    }

    .next-toggle.enabled {
      color: #9b4f2d;
      border-bottom-color: rgba(195, 104, 70, 0.72);
      opacity: 1;
      cursor: pointer;
      pointer-events: auto;
    }

    .next-toggle.enabled:active {
      transform: scale(0.985);
    }

    .team-credit {
      width: max-content;
      margin: 0 auto calc(env(safe-area-inset-bottom, 0px) + 6px);
      padding: 0;
      border: 0;
      background: transparent;
      color: rgba(96, 80, 64, 0.42);
      font-size: 0.62rem;
      letter-spacing: 0.01em;
      user-select: none;
      text-align: center;
    }

    .modal {
      position: fixed;
      inset: 0;
      background: var(--overlay);
      display: none;
      align-items: flex-end;
      justify-content: center;
      padding: 14px;
      z-index: 1000;
    }

    .modal.show {
      display: flex;
    }

    .sheet {
      width: 100%;
      max-width: 520px;
      background: #ffffff;
      border-radius: 22px;
      overflow: hidden;
      box-shadow: 0 24px 48px rgba(14, 30, 35, 0.26);
      animation: pop 170ms ease-out;
    }

    @keyframes pop {
      from { transform: translateY(8px); opacity: 0.3; }
      to { transform: translateY(0); opacity: 1; }
    }

    .modal-image {
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: cover;
      background: #eef1f1;
    }

    .modal-image-wrap {
      position: relative;
    }

    .talk-bubble {
      position: absolute;
      top: 10px;
      right: 10px;
      max-width: 72%;
      padding: 10px 12px;
      border-radius: 16px;
      border: 1px solid rgba(64, 148, 123, 0.3);
      background: linear-gradient(180deg, rgba(232, 255, 246, 0.96), rgba(218, 247, 236, 0.96));
      color: #1f6f58;
      font-size: 0.88rem;
      font-weight: 700;
      line-height: 1.42;
      box-shadow: 0 8px 16px rgba(55, 130, 106, 0.2);
      transform-origin: 100% 0;
      animation: bubble-pop 180ms ease-out;
    }

    .talk-bubble::after {
      content: "";
      position: absolute;
      right: 12px;
      bottom: -8px;
      width: 12px;
      height: 12px;
      background: rgba(218, 247, 236, 0.96);
      border-right: 1px solid rgba(64, 148, 123, 0.3);
      border-bottom: 1px solid rgba(64, 148, 123, 0.3);
      transform: rotate(45deg);
    }

    .modal-body {
      padding: 14px;
    }

    .modal-title {
      margin: 0;
      font-size: 1.32rem;
      letter-spacing: -0.02em;
    }

    .modal-desc {
      margin: 8px 0 14px;
      color: var(--sub-ink);
      line-height: 1.5;
      font-size: 0.93rem;
    }

    .modal-actions {
      display: flex;
      gap: 8px;
    }

    .ghost-btn, .pick-btn {
      border: 0;
      border-radius: 12px;
      padding: 11px 12px;
      font-weight: 700;
      font-size: 0.93rem;
      flex: 1;
    }

    .ghost-btn {
      background: #efe4d4;
      color: #5f4733;
    }

    .pick-btn {
      background: var(--accent-soft);
      color: #0f5939;
    }

    .ghost-btn:active, .pick-btn:active { transform: scale(0.98); }

    @keyframes bubble-pop {
      from { transform: scale(0.9); opacity: 0.4; }
      to { transform: scale(1); opacity: 1; }
    }

    @keyframes stamp-pop {
      from { transform: rotate(-12deg) scale(1.35); opacity: 0.25; }
      to { transform: rotate(-8deg) scale(1); opacity: 1; }
    }

    @media (min-width: 640px) {
      .modal {
        align-items: center;
      }
      .top-bar {
        height: calc(env(safe-area-inset-top, 0px) + 76px);
      }
    }
  </style>
</head>
<body>
  <header class="top-bar" aria-label="고정 상단 바">
    <div class="top-logo" aria-label="로고 영역">
      <img id="appLogo" class="logo-image" alt="서비스 로고" />
      <span id="logoPlaceholder" class="logo-placeholder">LOGO</span>
    </div>
    <p class="top-bar-text">친구 선택</p>
  </header>

  <main class="wrap">
    <section class="flow-surface">
      <span class="tape left"></span>
      <span class="tape right"></span>
      <section class="hero">
        <h1>오늘부터 마음을 나눌<br />다정한 친구를 골라주세요 ♧</h1>
        <p>하루를 함께 기록하고, 기분을 다정하게 들어줄 단 한 명의 친구를 골라주세요.</p>
        <p id="status" class="status"></p>
      </section>
      <div class="flow-divider"></div>
      <section id="cards" class="grid" aria-live="polite"></section>
    </section>
    <p class="hint">캐릭터 이미지를 터치하면 친구 소개가 팝업으로 열려요.</p>
    <div class="next-wrap">
      <p id="nextPageToggle" class="next-toggle" role="button" tabindex="0" aria-disabled="true">확인</p>
    </div>
  </main>
  <div class="team-credit">Copyright 2026 5FCV. All rights reserved.</div>

  <div id="characterModal" class="modal" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
    <div class="sheet">
      <div class="modal-image-wrap">
        <img id="modalImage" class="modal-image" alt="캐릭터 이미지" />
        <div id="modalBubble" class="talk-bubble"></div>
      </div>
      <div class="modal-body">
        <h2 id="modalTitle" class="modal-title"></h2>
        <p id="modalDesc" class="modal-desc"></p>
        <div class="modal-actions">
          <button id="closeModalBtn" class="ghost-btn" type="button">닫기</button>
          <button id="selectModalBtn" class="pick-btn" type="button">이 친구와 함께하기</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    let selectedCharacter = null;
    let characterList = [];
    let activeCharacter = null;
    const pageParams = new URLSearchParams(window.location.search);
    const flowMode = pageParams.get("mode");
    const isSelectionFlow = flowMode === "first" || flowMode === "change";
    const tapeLayouts = [
      {
        left: { top: "-8px", right: "auto", bottom: "auto", left: "36px", width: "64px", height: "18px", transform: "rotate(-7deg)" },
        right: { top: "-8px", right: "20px", bottom: "auto", left: "auto", width: "64px", height: "18px", transform: "rotate(8deg)" }
      },
      {
        left: { top: "-6px", right: "auto", bottom: "auto", left: "34px", width: "64px", height: "18px", transform: "rotate(-11deg)" },
        right: { top: "30%", right: "-9px", bottom: "auto", left: "auto", width: "18px", height: "64px", transform: "rotate(7deg)" }
      },
      {
        left: { top: "-7px", right: "auto", bottom: "auto", left: "52px", width: "64px", height: "18px", transform: "rotate(-10deg)" },
        right: { top: "-8px", right: "18px", bottom: "auto", left: "auto", width: "64px", height: "18px", transform: "rotate(10deg)" }
      },
      {
        left: { top: "-9px", right: "auto", bottom: "auto", left: "45%", width: "64px", height: "18px", transform: "translateX(-50%) rotate(-3deg)" },
        right: { top: "38%", right: "-9px", bottom: "auto", left: "auto", width: "18px", height: "58px", transform: "rotate(6deg)" }
      },
      {
        left: { top: "-7px", right: "auto", bottom: "auto", left: "68px", width: "64px", height: "18px", transform: "rotate(-6deg)" },
        right: { top: "-7px", right: "26px", bottom: "auto", left: "auto", width: "64px", height: "18px", transform: "rotate(12deg)" }
      }
    ];
    const pinPositionPatterns = ["p1", "p2", "p3", "p4", "p5", "p6"];
    const pinColorPatterns = ["c1", "c2", "c3", "c4"];
    const fallbackCharacters = [
      {
        id: "참깨",
        name: "참깨",
        description: "장난기 많은 천진난만함으로 웃음을 건네는 친구",
        image_url: "/static/characters/chamkkae.jpeg"
      },
      {
        id: "들깨",
        name: "들깨",
        description: "걱정을 먼저 알아채고 한없이 보살펴주는 다정한 친구",
        image_url: "/static/characters/deulkkae.jpeg"
      },
      {
        id: "통깨",
        name: "통깨",
        description: "귀엽고 공감 리액션이 뛰어나 기분을 밝혀주는 친구",
        image_url: "/static/characters/tongkkae.jpeg"
      },
      {
        id: "흑깨",
        name: "흑깨",
        description: "하나부터 열까지 차근차근 알려주는 친절한 친구",
        image_url: "/static/characters/heukkkae.jpeg"
      }
    ];
    const defaultBubbleMessages = [
      "안녕! 나랑 같이 놀자! 🐾✨",
      "오늘도 내가 꼭 안아줄게! 🤍",
      "나 선택해주면 매일 응원해줄게! 🌼",
      "우리 둘이 팀 하면 완전 든든해! 💪🐶",
      "네 하루를 반짝반짝하게 해줄게! 🌟",
      "지금부터 내가 네 찐친 할래! 🫶",
      "토닥토닥, 내가 옆에 있을게! 🍀",
      "헤헤, 나랑 함께해줘! 😊"
    ];
    const bubbleMessagesByCharacter = {
      "참깨": [
        "히히! 오늘 기분은 어때?\\n내가 장난꾸러기 모드로 웃겨줄게 😜",
        "짜잔~ 내가 왔어!\\n우리 재밌게 하루 시작하자 🎈",
        "킥킥, 오늘은 장난 한 스푼!\\n내가 웃음 버튼 눌러줄게 🤭",
        "심심하면 바로 불러!\\n내가 분위기 메이커 할게 🎉",
        "출석~ 장난꾸러기 참깨 등장!\\n오늘도 재미 보장 🐾",
        "하이파이브 먼저 하자!\\n신나는 하루로 바꿔줄게 ✨"
      ],
      "들깨": [
        "괜찮아, 천천히 해도 돼.\\n내가 옆에서 다정하게 챙길게 🌿",
        "걱정되는 마음 있으면 말해줘.\\n내가 부드럽게 들어줄게 🤍",
        "오늘은 무리하지 않아도 괜찮아.\\n내가 차분히 같이 갈게 ☁️",
        "작은 변화도 소중해.\\n내가 다정하게 지켜볼게 🍀",
        "천천히 숨 쉬고 시작하자.\\n내가 옆에서 토닥여줄게 🫶",
        "혹시 마음이 무거우면\\n내가 먼저 안부 물어볼게 🌼"
      ],
      "통깨": [
        "헉, 그랬구나!\\n네 마음 완전 공감이야 💖",
        "우와 잘했어!\\n내가 귀엽게 리액션 팡팡 해줄게 ✨",
        "와아~ 그 얘기 진짜 중요해!\\n내가 크게 공감해줄게 🙌",
        "오구오구 수고했어!\\n리액션 천재 모드 ON 💫",
        "좋은 일도 힘든 일도\\n내가 귀엽게 받아줄게 🧸",
        "네 감정 하나하나에\\n내 하트 리액션 발사! 💘"
      ],
      "흑깨": [
        "좋아, 지금부터 하나씩 해보자.\\n내가 차근차근 알려줄게 📘",
        "천천히 따라와도 괜찮아.\\n내가 부드럽게 안내할게 🫶",
        "먼저 쉬운 단계부터 시작하자.\\n순서대로 내가 도와줄게 ✅",
        "헷갈리는 부분 있으면\\n내가 다시 쉽게 설명할게 🌿",
        "급하지 않게 한 걸음씩!\\n내가 옆에서 길잡이 할게 📎",
        "시작부터 마무리까지\\n내가 차분히 함께할게 🤍"
      ]
    };
    const userId = "1";

    function apiHeaders(extra = {}) {
      return { "X-User-Id": userId, ...extra };
    }

    function getCanonicalCharacterImageUrl(characterId, fallbackUrl = "") {
      const fixedMap = {
        "참깨": "/static/characters/chamkkae.jpeg",
        "들깨": "/static/characters/deulkkae.jpeg",
        "통깨": "/static/characters/tongkkae.jpeg",
        "흑깨": "/static/characters/heukkkae.jpeg"
      };
      const version = "friend-map-20260227";
      if (fixedMap[characterId]) return fixedMap[characterId] + "?v=" + version;
      if (fallbackUrl) return fallbackUrl + (fallbackUrl.includes("?") ? "&" : "?") + "v=" + version;
      return "";
    }

    function getFlowQuery() {
      if (flowMode === "change") return "?mode=change";
      if (flowMode === "first") return "?mode=first";
      return "";
    }

    function applyTapeStyle(el, style) {
      el.style.top = style.top;
      el.style.right = style.right;
      el.style.bottom = style.bottom;
      el.style.left = style.left;
      el.style.width = style.width;
      el.style.height = style.height;
      el.style.transform = style.transform;
    }

    function applyRandomTapeLayout() {
      const leftTape = document.querySelector(".tape.left");
      const rightTape = document.querySelector(".tape.right");
      if (!leftTape || !rightTape) return;
      const layout = tapeLayouts[Math.floor(Math.random() * tapeLayouts.length)];
      applyTapeStyle(leftTape, layout.left);
      applyTapeStyle(rightTape, layout.right);
    }

    function randomFrom(list) {
      return list[Math.floor(Math.random() * list.length)];
    }

    async function fetchJsonOrThrow(url, options = {}) {
      const response = await fetch(url, options);
      const contentType = response.headers.get("content-type") || "";
      const bodyText = await response.text();
      let body = null;

      if (bodyText) {
        if (contentType.includes("application/json")) {
          body = JSON.parse(bodyText);
        } else {
          try {
            body = JSON.parse(bodyText);
          } catch (parseError) {
            body = bodyText;
          }
        }
      }

      if (!response.ok) {
        const detail =
          body && typeof body === "object" && body.detail
            ? JSON.stringify(body.detail)
            : String(body || "no detail");
        throw new Error(response.status + " " + response.statusText + " - " + detail);
      }

      return body;
    }

    async function loadData() {
      const [characters, my] = await Promise.all([
        fetchJsonOrThrow("/api/v1/users/characters", { headers: apiHeaders() }),
        fetchJsonOrThrow("/api/v1/users/me/character", { headers: apiHeaders() })
      ]);

      if (!Array.isArray(characters) || characters.length === 0) {
        throw new Error("characters payload is empty");
      }

      characterList = characters.map((character) => ({
        ...character,
        image_url: getCanonicalCharacterImageUrl(character.id, character.image_url || "")
      }));
      selectedCharacter = (my && my.selected_character) || null;

      if (selectedCharacter && !isSelectionFlow) {
        window.location.replace("/ui/main");
        return;
      }

      renderCards(characterList);
      updateStatus();
    }

    function updateStatus() {
      const statusEl = document.getElementById("status");
      if (!selectedCharacter) {
        statusEl.textContent = "아직 친구를 고르지 않았어요.";
        updateNextButton();
        return;
      }
      statusEl.textContent = "현재 함께하는 친구: " + selectedCharacter;
      updateNextButton();
    }

    function updateNextButton() {
      const nextBtn = document.getElementById("nextPageToggle");
      if (!selectedCharacter) {
        nextBtn.classList.remove("enabled");
        nextBtn.setAttribute("aria-disabled", "true");
        nextBtn.textContent = "확인";
        return;
      }
      nextBtn.classList.add("enabled");
      nextBtn.setAttribute("aria-disabled", "false");
      nextBtn.textContent = "확인 후 다음 →";
    }

    function getRandomBubbleMessage(characterId) {
      const characterMessages = bubbleMessagesByCharacter[characterId] || [];
      const useCharacterMessage =
        characterMessages.length > 0 &&
        (defaultBubbleMessages.length === 0 || Math.random() < 0.75);
      const pool = useCharacterMessage ? characterMessages : defaultBubbleMessages;
      return pool[Math.floor(Math.random() * pool.length)];
    }

    function openModal(character) {
      activeCharacter = character;
      document.getElementById("modalImage").src = getCanonicalCharacterImageUrl(
        character.id,
        character.image_url || ""
      );
      document.getElementById("modalBubble").textContent = getRandomBubbleMessage(character.id);
      document.getElementById("modalTitle").textContent = character.name;
      document.getElementById("modalDesc").textContent = character.description;
      document.getElementById("selectModalBtn").textContent =
        character.id === selectedCharacter ? "이미 함께하는 친구예요" : "이 친구와 함께하기";
      document.getElementById("characterModal").classList.add("show");
    }

    function closeModal() {
      document.getElementById("characterModal").classList.remove("show");
      activeCharacter = null;
    }

    async function selectCharacter(characterId) {
      await fetch("/api/v1/users/me/character", {
        method: "PUT",
        headers: apiHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ character_id: characterId })
      });
      selectedCharacter = characterId;
      renderCards(characterList);
      updateStatus();
    }

    function renderCards(characters) {
      const cards = document.getElementById("cards");
      cards.innerHTML = "";

      characters.forEach((character) => {
        const wrapper = document.createElement("button");
        wrapper.className = "card-btn";
        wrapper.type = "button";
        wrapper.onclick = () => openModal(character);

        const card = document.createElement("article");
        card.className = "card" + (character.id === selectedCharacter ? " selected" : "");

        const stamp = document.createElement("span");
        stamp.className = "stamp";
        stamp.textContent = "선택완료 🐾";

        const photoWrap = document.createElement("div");
        photoWrap.className = "photo-wrap";

        const pin = document.createElement("span");
        const pinPosClass = randomFrom(pinPositionPatterns);
        const pinColorClass = randomFrom(pinColorPatterns);
        pin.className = "pin " + pinPosClass + " " + pinColorClass;

        const image = document.createElement("img");
        image.className = "thumb";
        image.alt = character.name + " 캐릭터 이미지";
        image.src = getCanonicalCharacterImageUrl(character.id, character.image_url || "");

        const row = document.createElement("div");
        row.className = "label-row";

        const name = document.createElement("h2");
        name.className = "name";
        name.textContent = character.name;

        photoWrap.append(pin, image);
        row.append(name);
        card.append(stamp, photoWrap, row);
        wrapper.appendChild(card);
        cards.appendChild(wrapper);
      });
    }

    document.getElementById("closeModalBtn").onclick = closeModal;
    document.getElementById("characterModal").onclick = (event) => {
      if (event.target.id === "characterModal") {
        closeModal();
      }
    };
    document.getElementById("selectModalBtn").onclick = async () => {
      if (!activeCharacter) return;
      await selectCharacter(activeCharacter.id);
      closeModal();
    };
    const nextToggle = document.getElementById("nextPageToggle");
    nextToggle.onclick = () => {
      if (!selectedCharacter) return;
      window.location.href = "/ui/friend/check" + (getFlowQuery() || "?mode=first");
    };
    nextToggle.onkeydown = (event) => {
      if (!selectedCharacter) return;
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        window.location.href = "/ui/friend/check" + (getFlowQuery() || "?mode=first");
      }
    };

    applyRandomTapeLayout();
    loadData().catch((error) => {
      const statusEl = document.getElementById("status");
      characterList = fallbackCharacters;
      renderCards(fallbackCharacters);
      updateNextButton();
      statusEl.textContent = "캐릭터를 불러오지 못했어요. 임시 목록을 보여줘요. (" + error.message + ")";
    });
  </script>
</body>
</html>
        """
    )


@app.get("/ui/friend/next")
async def friend_next_ui() -> RedirectResponse:
    return RedirectResponse(url="/ui/main", status_code=307)
