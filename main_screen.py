import html
from datetime import date, datetime
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from friend_db import (
    FriendMedicationIntakeLog,
    FriendMedicationPlan,
    FriendMoodSticker,
    FriendUser,
    FriendUserMedicationSchedule,
    FriendUserProfile,
    FriendUserUiPreference,
    FriendUserVisitSchedule,
    ensure_friend_user,
)

router = APIRouter()


@router.get("/ui/main", response_class=HTMLResponse)
async def main_screen_ui() -> HTMLResponse:
    user = await ensure_friend_user(1)
    selected_name = user.selected_character_id or "내 친구"
    selected_image_map = {
        "참깨": "/static/characters/chamkkae-removebg.png",
        "들깨": "/static/characters/deulkkae-removebg.png",
        "통깨": "/static/characters/tongkkae-removebg.png",
        "흑깨": "/static/characters/heukkkae-removebg.png",
    }
    selected_image = selected_image_map.get(selected_name, "/static/characters/chamkkae-removebg.png")

    initial_visit_date = ""
    initial_dday_meta = "다음 진료일까지"
    initial_dday_prefix = "D-"
    initial_dday_number = "00"
    initial_dday_class = ""
    visit_schedule = await FriendUserVisitSchedule.get_or_none(user_id=user.id)
    if visit_schedule and visit_schedule.next_visit_date:
        next_visit = visit_schedule.next_visit_date
        initial_visit_date = next_visit.isoformat()
        diff_days = (next_visit - date.today()).days
        if diff_days < 0:
            initial_dday_meta = "진료일이 지났어요"
            initial_dday_prefix = "D+"
            initial_dday_number = str(abs(diff_days)).zfill(2)
            initial_dday_class = "overdue"
        else:
            initial_dday_meta = "다음 진료일까지"
            initial_dday_prefix = "D-"
            initial_dday_number = str(diff_days).zfill(2)
            if diff_days <= 0:
                initial_dday_class = "level-0"
            elif diff_days == 1:
                initial_dday_class = "level-1"
            elif diff_days == 2:
                initial_dday_class = "level-2"
            elif diff_days <= 4:
                initial_dday_class = "level-3-4"
            elif diff_days <= 6:
                initial_dday_class = "level-5-6"
            else:
                initial_dday_class = "level-7plus"

    page = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <link rel="preload" href="/assets/fonts/MemomentKkukkukk.otf?v=20260301" as="font" type="font/otf" />
  <title>메인 화면</title>
  <style>
    @font-face {
      font-family: "Cafe24SuperMagic";
      src: url("https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_2307-2@1.0/Cafe24Supermagic-Regular-v1.0.woff2") format("woff2");
      font-weight: 400;
      font-display: swap;
    }

    @font-face {
      font-family: "Cafe24SuperMagic";
      src: url("https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_2307-2@1.0/Cafe24Supermagic-Bold-v1.0.woff2") format("woff2");
      font-weight: 700;
      font-display: swap;
    }

    @font-face {
      font-family: "MemomentKkukkukk";
      src: url("/assets/fonts/MemomentKkukkukk.otf?v=20260301") format("opentype"), local("MemomentKkukkukk");
      font-weight: 400;
      font-display: swap;
    }

    :root {
      --ink: #4a3a2a;
      --sub-ink: #7b6a57;
      --line: rgba(188, 165, 140, 0.48);
      --accent: #9b4f2d;
    }

    * { box-sizing: border-box; }

    body, body * {
      font-family: "MemomentKkukkukk", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    }

    html, body, button, input, select, textarea {
      font-family: "MemomentKkukkukk", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
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
        linear-gradient(180deg, #f8f3ea, #f4efe2);
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
      font-weight: 800;
      letter-spacing: 0.06em;
    }

    .top-bar-text {
      margin: 0;
      font-size: 1.08rem;
      font-weight: 700;
      color: #5b4633;
      line-height: 1;
      text-align: center;
    }

    .top-toggle {
      position: relative;
      display: inline-flex;
      justify-content: center;
      align-items: center;
      flex-direction: column;
      gap: 3px;
      min-height: 92px;
      aspect-ratio: 1 / 1;
      padding: 2px 1px;
      border-radius: 0;
      text-decoration: none;
      color: #5d4733;
      border: 0;
      background: transparent;
      box-shadow: none;
      font-size: 1.2rem;
      font-weight: 700;
      text-align: center;
      width: 100%;
      font-family: inherit;
      appearance: none;
      -webkit-appearance: none;
      cursor: pointer;
    }

    .top-toggle::after {
      content: "";
      position: absolute;
      top: 19%;
      bottom: 19%;
      right: 0;
      width: 1px;
      background: rgba(169, 138, 106, 0.38);
    }

    .top-toggle:last-child::after {
      display: none;
    }

    .top-toggle:active {
      transform: scale(0.985);
    }

    .bookmarkable::before {
      content: "";
      position: absolute;
      top: 5px;
      right: 8px;
      width: 13px;
      height: 18px;
      background: linear-gradient(180deg, #ff8a7b, #ff6e5c);
      clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 78%, 0 100%);
      border-radius: 1px;
      box-shadow: 0 1px 2px rgba(131, 58, 46, 0.24);
      opacity: 0;
      transform: translateY(-2px) scale(0.92);
      transition: opacity 120ms ease, transform 120ms ease;
      pointer-events: none;
    }

    .bookmarkable:is(:focus-visible, :active, .bookmarked)::before {
      opacity: 1;
      transform: translateY(0) scale(1);
    }

    .top-toggle-row {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0;
      width: min(100%, 560px);
      margin: 0 auto;
      padding: 0;
      align-items: center;
    }

    .toggle-label {
      line-height: 1.08;
      font-size: 1.36rem;
    }

    .dday-toggle {
      gap: 4px;
      padding-top: 4px;
      padding-bottom: 4px;
    }

    .dday-meta {
      font-size: 0.78rem;
      line-height: 1.1;
      color: #7b6550;
      max-width: none;
      white-space: nowrap;
      letter-spacing: 0.01em;
    }

    .dday-value {
      font-size: 1.46rem;
      line-height: 1;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      position: relative;
      color: #54493a;
      font-weight: 800;
      letter-spacing: 0.01em;
      padding: 0 12px;
      white-space: nowrap;
      word-break: keep-all;
      border-radius: 5px;
      border: 1px solid rgba(177, 157, 108, 0.44);
      background:
        linear-gradient(180deg, rgba(252, 242, 184, 0.94), rgba(247, 231, 166, 0.94)),
        repeating-linear-gradient(
          92deg,
          rgba(255, 255, 255, 0.06) 0px,
          rgba(255, 255, 255, 0.06) 2px,
          rgba(216, 191, 121, 0.06) 2px,
          rgba(216, 191, 121, 0.06) 4px
        );
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.5),
        0 1px 3px rgba(129, 108, 70, 0.14);
      text-shadow: 0 1px 0 rgba(255, 255, 255, 0.4);
      transform: rotate(-1deg);
      margin: 0 auto;
    }

    .dday-prefix,
    .dday-number {
      position: relative;
      z-index: 1;
    }

    .dday-number {
      font-weight: 900;
      font-size: 1.2em;
      line-height: 1;
    }

    .dday-number.level-7plus {
      color: #8f816d;
    }

    .dday-number.level-5-6 {
      color: #aa7d4f;
    }

    .dday-number.level-3-4 {
      color: #c47c3d;
    }

    .dday-number.level-2 {
      color: #dd7b2c;
    }

    .dday-number.level-1 {
      color: #cf2d24;
    }

    .dday-number.level-0,
    .dday-number.overdue {
      color: #a51616;
    }

    .dday-value::before {
      content: "";
      position: absolute;
      top: -1px;
      right: -1px;
      width: 12px;
      height: 12px;
      background: linear-gradient(135deg, rgba(224, 203, 144, 0.92), rgba(205, 184, 125, 0.92));
      border-left: 1px solid rgba(171, 151, 104, 0.42);
      border-bottom: 1px solid rgba(171, 151, 104, 0.42);
      clip-path: polygon(0 0, 100% 0, 100% 100%);
      pointer-events: none;
    }

    .dday-value::after {
      content: "";
      position: absolute;
      left: 8px;
      right: 8px;
      bottom: 6px;
      height: 1px;
      background: rgba(176, 151, 95, 0.3);
      pointer-events: none;
    }

    .toggle-illustration-wrap {
      width: 80px;
      height: 80px;
      border-radius: 0;
      border: 0;
      background: transparent;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: visible;
    }

    .toggle-illustration {
      width: 70px;
      height: 70px;
      display: block;
      object-fit: contain;
    }

    .wrap {
      max-width: 760px;
      margin: 0 auto;
      width: 100%;
      flex: 1;
      padding: calc(env(safe-area-inset-top, 0px) + 96px) 20px 30px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .note-surface {
      position: relative;
      isolation: isolate;
      border-radius: 22px;
      border: 1px solid var(--line);
      background:
        repeating-linear-gradient(
          to bottom,
          rgba(255, 252, 245, 0.98) 0px,
          rgba(255, 252, 245, 0.98) 30px,
          rgba(197, 175, 150, 0.14) 31px
        );
      box-shadow: 0 12px 24px rgba(110, 90, 70, 0.16);
      padding: 18px 14px 14px 34px;
      overflow: hidden;
    }

    .note-surface::before {
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

    .friend-toggle {
      position: relative;
      z-index: 2;
      border: 0;
      width: 100%;
      background: transparent;
      padding: 0;
      cursor: pointer;
    }

    .friend-image-wrap {
      margin: 6px auto 0;
      width: min(78vw, 270px);
      aspect-ratio: 1 / 1;
      border-radius: 0;
      overflow: visible;
      border: 0;
      box-shadow: none;
      position: relative;
      background: transparent;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .friend-image-wrap::after {
      content: "";
      position: absolute;
      left: 50%;
      bottom: -10px;
      width: 68%;
      height: 20px;
      transform: translateX(-50%);
      border-radius: 999px;
      background: radial-gradient(
        ellipse at center,
        rgba(145, 111, 77, 0.26) 0%,
        rgba(145, 111, 77, 0.14) 52%,
        rgba(145, 111, 77, 0) 100%
      );
      pointer-events: none;
    }

    .friend-image {
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: block;
      filter: drop-shadow(0 10px 18px rgba(91, 71, 38, 0.2));
    }

    .friend-bubble {
      position: absolute;
      left: 50%;
      top: 60px;
      transform: translateX(-50%) rotate(-1deg);
      max-width: min(88%, 320px);
      min-width: min(70%, 250px);
      padding: 10px 12px 11px;
      border-radius: 14px;
      border: 1px solid rgba(158, 127, 98, 0.34);
      background: rgba(255, 249, 240, 0.62);
      box-shadow: 0 8px 16px rgba(97, 73, 47, 0.12);
      backdrop-filter: blur(2px);
      color: #58412e;
      font-size: 0.92rem;
      line-height: 1.32;
      white-space: pre-line;
      text-align: center;
      pointer-events: none;
      z-index: 6;
    }

    .friend-bubble::after {
      content: "";
      position: absolute;
      left: 50%;
      bottom: -7px;
      width: 11px;
      height: 11px;
      margin-left: -5.5px;
      transform: rotate(45deg);
      background: rgba(255, 249, 240, 0.62);
      border-right: 1px solid rgba(158, 127, 98, 0.34);
      border-bottom: 1px solid rgba(158, 127, 98, 0.34);
    }

    .friend-nameplate {
      position: absolute;
      top: 30px;
      right: 16px;
      --plate-rotate: 5deg;
      transform: rotate(var(--plate-rotate));
      z-index: 8;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 116px;
      max-width: min(52%, 220px);
      padding: 9px 14px 10px;
      border-radius: 4px;
      border: 1px solid rgba(114, 83, 56, 0.72);
      background:
        radial-gradient(
          circle at 16px 8px,
          rgba(86, 61, 39, 0.66) 0 2px,
          rgba(149, 114, 81, 0.38) 2.2px 4px,
          transparent 4.2px
        ),
        radial-gradient(
          circle at calc(100% - 16px) 8px,
          rgba(86, 61, 39, 0.66) 0 2px,
          rgba(149, 114, 81, 0.38) 2.2px 4px,
          transparent 4.2px
        ),
        repeating-linear-gradient(
          0deg,
          rgba(255, 255, 255, 0.06) 0px,
          rgba(255, 255, 255, 0.06) 2px,
          rgba(129, 96, 65, 0.08) 2px,
          rgba(129, 96, 65, 0.08) 4px
        ),
        repeating-linear-gradient(
          90deg,
          rgba(169, 124, 82, 0.18) 0px,
          rgba(169, 124, 82, 0.18) 18px,
          rgba(133, 97, 65, 0.2) 18px,
          rgba(133, 97, 65, 0.2) 36px
        ),
        linear-gradient(180deg, rgba(141, 101, 67, 0.97), rgba(103, 72, 47, 0.96));
      box-shadow:
        inset 0 1px 0 rgba(222, 182, 141, 0.22),
        inset 0 -8px 10px rgba(59, 40, 25, 0.3),
        0 8px 14px rgba(84, 58, 35, 0.24);
      color: #fff4de;
      text-shadow: 0 1px 1px rgba(53, 34, 20, 0.56);
      font-size: 1.28rem;
      font-weight: 700;
      font-family: "Cafe24SuperMagic", "MemomentKkukkukk", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif !important;
      line-height: 1;
      text-align: center;
      white-space: nowrap;
      overflow: visible;
      letter-spacing: 0.01em;
      animation: nameplate-pin-wobble 1.9s cubic-bezier(0.42, 0.02, 0.3, 1) infinite;
      transform-origin: 88% -8px;
      text-decoration: none;
      cursor: pointer;
      user-select: none;
    }

    .friend-nameplate:active {
      filter: brightness(0.98);
    }

    .friend-nameplate:focus-visible {
      outline: 2px dashed rgba(255, 232, 205, 0.82);
      outline-offset: 3px;
    }

    .friend-nameplate.anim-off {
      animation: none;
      transform: rotate(var(--plate-rotate));
    }

    .friend-nameplate::before,
    .friend-nameplate::after {
      content: "";
      position: absolute;
      top: -30px;
      width: 2px;
      height: 30px;
      background:
        repeating-linear-gradient(
          180deg,
          rgba(171, 137, 101, 0.98) 0px,
          rgba(171, 137, 101, 0.98) 2px,
          rgba(132, 101, 71, 0.98) 2px,
          rgba(132, 101, 71, 0.98) 4px
        );
      border-radius: 999px;
      opacity: 1;
      filter: drop-shadow(0 1px 0 rgba(255, 246, 232, 0.34));
      pointer-events: none;
    }

    .friend-nameplate::before {
      left: 16px;
      transform: rotate(12deg);
      transform-origin: bottom center;
    }

    .friend-nameplate::after {
      right: 16px;
      transform: rotate(-12deg);
      transform-origin: bottom center;
    }

    @keyframes nameplate-pin-wobble {
      0% { transform: rotate(0.8deg) translateY(0); }
      18% { transform: rotate(6.9deg) translateY(-0.8px); }
      46% { transform: rotate(12.8deg) translateY(0); }
      72% { transform: rotate(4.4deg) translateY(0.6px); }
      100% { transform: rotate(0.8deg) translateY(0); }
    }

    @media (prefers-reduced-motion: reduce) {
      .friend-nameplate {
        animation: none;
      }
    }

    .friend-surface {
      position: relative;
      isolation: isolate;
      border-radius: 38px;
      border: 1px solid rgba(201, 170, 139, 0.12);
      padding: 84px 20px 30px;
      background:
        repeating-linear-gradient(
          45deg,
          rgba(255, 255, 255, 0.07) 0px,
          rgba(255, 255, 255, 0.07) 2px,
          rgba(242, 223, 200, 0.07) 2px,
          rgba(242, 223, 200, 0.07) 4px
        ),
        radial-gradient(circle at 18% 16%, rgba(255, 255, 255, 0.66), rgba(255, 255, 255, 0)),
        radial-gradient(circle at 82% 18%, rgba(255, 243, 232, 0.52), rgba(255, 243, 232, 0)),
        radial-gradient(circle at 50% 100%, rgba(245, 222, 198, 0.42), rgba(245, 222, 198, 0)),
        linear-gradient(180deg, rgba(252, 244, 232, 0.96), rgba(248, 231, 212, 0.94));
      box-shadow:
        inset 0 2px 0 rgba(255, 255, 255, 0.72),
        inset 0 -14px 24px rgba(220, 185, 150, 0.22),
        0 7px 14px rgba(116, 90, 64, 0.05);
    }

    .friend-surface::before {
      content: "";
      position: absolute;
      left: 50%;
      top: 88px;
      transform: translateX(-50%);
      width: min(84%, 340px);
      height: min(52vw, 220px);
      border-radius: 168px 168px 34px 34px / 138px 138px 34px 34px;
      border: 1px solid rgba(209, 124, 70, 0.34);
      background:
        repeating-linear-gradient(
          0deg,
          rgba(255, 219, 185, 0.12) 0px,
          rgba(255, 219, 185, 0.12) 3px,
          rgba(242, 173, 114, 0.12) 3px,
          rgba(242, 173, 114, 0.12) 6px
        ),
        repeating-linear-gradient(
          90deg,
          rgba(255, 223, 193, 0.1) 0px,
          rgba(255, 223, 193, 0.1) 4px,
          rgba(241, 170, 108, 0.1) 4px,
          rgba(241, 170, 108, 0.1) 8px
        ),
        radial-gradient(circle at 50% 26%, rgba(255, 252, 247, 0.62), rgba(255, 252, 247, 0) 62%),
        radial-gradient(circle at 18% 72%, rgba(255, 233, 210, 0.36), rgba(255, 233, 210, 0)),
        radial-gradient(circle at 82% 72%, rgba(255, 233, 210, 0.36), rgba(255, 233, 210, 0)),
        linear-gradient(180deg, rgba(247, 183, 129, 0.6), rgba(231, 145, 88, 0.38));
      box-shadow:
        inset 0 12px 20px rgba(255, 248, 239, 0.3),
        inset 0 -10px 16px rgba(194, 117, 63, 0.24);
      z-index: 0;
      pointer-events: none;
    }

    .friend-surface::after {
      content: "";
      position: absolute;
      left: 50%;
      bottom: 10px;
      transform: translateX(-50%);
      width: min(84%, 340px);
      height: 56px;
      border-radius: 999px;
      border: 1px solid rgba(209, 124, 70, 0.42);
      background:
        radial-gradient(120% 110% at 50% -30%, rgba(255, 255, 255, 0.6), rgba(255, 255, 255, 0) 62%),
        radial-gradient(circle at 28% 24%, rgba(255, 255, 255, 0.52), rgba(255, 255, 255, 0)),
        radial-gradient(circle at 72% 28%, rgba(255, 245, 232, 0.42), rgba(255, 245, 232, 0)),
        repeating-linear-gradient(
          90deg,
          rgba(255, 219, 185, 0.16) 0px,
          rgba(255, 219, 185, 0.16) 7px,
          rgba(242, 173, 114, 0.16) 7px,
          rgba(242, 173, 114, 0.16) 14px
        ),
        linear-gradient(180deg, rgba(255, 183, 118, 0.74), rgba(238, 139, 71, 0.52));
      box-shadow:
        inset 0 3px 0 rgba(255, 255, 255, 0.58),
        inset 0 -12px 14px rgba(193, 108, 54, 0.3),
        0 12px 18px rgba(152, 86, 43, 0.16);
      z-index: 0;
      pointer-events: none;
    }

    .friend-fabric-noise {
      position: absolute;
      inset: 0;
      border-radius: inherit;
      background:
        radial-gradient(circle at 14% 20%, rgba(255, 255, 255, 0.08) 0 2px, transparent 3px),
        radial-gradient(circle at 86% 24%, rgba(255, 255, 255, 0.06) 0 2px, transparent 3px),
        radial-gradient(circle at 25% 80%, rgba(223, 188, 152, 0.08) 0 2px, transparent 3px),
        radial-gradient(circle at 76% 76%, rgba(223, 188, 152, 0.08) 0 2px, transparent 3px);
      opacity: 0.8;
      z-index: 0;
      pointer-events: none;
    }

    .spring-note {
      border: 1px solid rgba(188, 165, 140, 0.48);
      background:
        repeating-linear-gradient(
          to bottom,
          rgba(255, 252, 245, 0.98) 0px,
          rgba(255, 252, 245, 0.98) 30px,
          rgba(197, 175, 150, 0.14) 31px
        );
      box-shadow:
        0 12px 24px rgba(110, 90, 70, 0.16),
        inset 0 1px 0 rgba(255, 255, 255, 0.8);
      backdrop-filter: blur(6px);
      overflow: visible;
    }

    .spring-note::before {
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

    .spring-note::after {
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

    .friend-toy {
      position: absolute;
      left: 18px;
      bottom: 22px;
      z-index: 12;
      pointer-events: auto;
      cursor: pointer;
      user-select: none;
      filter: drop-shadow(0 4px 8px rgba(124, 92, 63, 0.16));
      transition: transform 120ms ease;
    }

    .friend-toy:active {
      transform: scale(0.94);
    }

    .friend-toy.secret-pop {
      animation: friend-toy-pop 280ms ease-out;
    }

    .friend-toy.ball {
      width: 42px;
      height: 42px;
      border-radius: 50%;
      border: 1px solid rgba(123, 157, 45, 0.58);
      background:
        radial-gradient(circle at 30% 28%, rgba(255, 255, 255, 0.74), rgba(255, 255, 255, 0) 46%),
        radial-gradient(130% 110% at -24% 50%, transparent 57%, rgba(248, 252, 255, 0.95) 59% 64%, transparent 66%),
        radial-gradient(130% 110% at 124% 50%, transparent 57%, rgba(248, 252, 255, 0.95) 59% 64%, transparent 66%),
        linear-gradient(140deg, rgba(214, 238, 104, 0.97), rgba(155, 198, 51, 0.95));
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.64),
        inset 0 -6px 8px rgba(84, 123, 23, 0.24);
    }

    .friend-toy.ball::after {
      content: "";
      position: absolute;
      inset: 0;
      border-radius: 50%;
      background:
        repeating-linear-gradient(
          45deg,
          rgba(255, 255, 255, 0.08) 0px,
          rgba(255, 255, 255, 0.08) 1px,
          rgba(188, 214, 78, 0.08) 1px,
          rgba(188, 214, 78, 0.08) 2px
        );
      opacity: 0.65;
      mix-blend-mode: soft-light;
    }

    .friend-toy.bone {
      width: 86px;
      height: 38px;
      transform: rotate(var(--toy-rotate, -12deg));
      background:
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 160 80'%3E%3Cpath d='M28 18c0-8 6-14 14-14 6 0 11 4 13 9h50c2-5 7-9 13-9 8 0 14 6 14 14 0 5-2 9-6 12 4 3 6 7 6 12 0 8-6 14-14 14-6 0-11-4-13-9H55c-2 5-7 9-13 9-8 0-14-6-14-14 0-5 2-9 6-12-4-3-6-7-6-12z' fill='%23fff7ee' stroke='%23c9a47c' stroke-width='4' stroke-linejoin='round'/%3E%3Cpath d='M58 31h44' stroke='%23e8d2bc' stroke-width='6' stroke-linecap='round'/%3E%3C/svg%3E")
        center / contain no-repeat;
      border: 0;
      filter: drop-shadow(0 3px 5px rgba(124, 92, 63, 0.16));
    }

    .toy-secret-note {
      position: absolute;
      right: 12px;
      top: 92px;
      z-index: 20;
      max-width: 160px;
      padding: 9px 10px;
      border-radius: 3px 10px 5px 9px;
      border: 1px solid rgba(182, 149, 92, 0.52);
      background:
        linear-gradient(180deg, rgba(255, 252, 205, 0.98), rgba(251, 236, 154, 0.96)),
        repeating-linear-gradient(180deg, rgba(0, 0, 0, 0.03) 0 1px, rgba(0, 0, 0, 0) 1px 6px);
      box-shadow:
        0 6px 12px rgba(112, 87, 53, 0.22),
        0 1px 0 rgba(255, 255, 255, 0.72) inset;
      color: #5f472e;
      font-size: 0.8rem;
      line-height: 1.35;
      white-space: pre-line;
      opacity: 0;
      transform: translateY(-6px) rotate(-2deg) scale(0.98);
      pointer-events: none;
      transition: opacity 180ms ease, transform 180ms ease;
    }

    .toy-secret-note.show {
      opacity: 1;
      transform: translateY(0) rotate(-2deg) scale(1);
    }

    @keyframes friend-toy-pop {
      0% { transform: scale(1); }
      50% { transform: scale(1.11); }
      100% { transform: scale(1); }
    }

    .friend-help {
      margin: 10px 0 4px;
      text-align: center;
      color: var(--sub-ink);
      font-size: 0.92rem;
      line-height: 1.45;
    }

    .section-title {
      margin: 0;
      font-size: 1.07rem;
      color: #5a4432;
    }

    .med-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
    }

    .mood-grid {
      margin-top: 10px;
      display: grid;
      grid-template-columns: repeat(7, minmax(0, 1fr));
      gap: 6px;
      align-items: start;
    }

    .mood-btn {
      --mood-color: #d8d8d8;
      border: 0;
      background: transparent;
      border-radius: 16px;
      padding: 6px 2px;
      min-height: 70px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      gap: 7px;
      color: #5b4734;
      font-size: 0.62rem;
      line-height: 1.12;
      text-align: center;
      cursor: pointer;
      transition: transform 120ms ease;
      font-family: inherit;
    }

    .mood-btn:nth-child(odd) {
      margin-top: 0;
    }

    .mood-btn:nth-child(even) {
      margin-top: 14px;
    }

    .mood-btn:active {
      transform: scale(0.96);
    }

    .mood-color {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: var(--mood-color);
      color: var(--mood-face-color, #fff8ef);
      border: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.3),
        0 5px 9px rgba(96, 75, 55, 0.22),
        0 1px 2px rgba(96, 75, 55, 0.18);
    }

    .mood-face-art {
      width: 22px;
      height: 22px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      user-select: none;
    }

    .mood-face-art svg {
      width: 100%;
      height: 100%;
      display: block;
      shape-rendering: geometricPrecision;
      filter: none;
    }

    .mood-label {
      display: block;
      font-size: 0.66rem;
      line-height: 1.16;
      letter-spacing: -0.01em;
      font-family: inherit;
    }

    .mood-help {
      margin: 8px 0 0;
      font-size: 0.83rem;
      color: var(--sub-ink);
    }

    .mood-remaining {
      margin: 6px 0 0;
      font-size: 0.78rem;
      color: #74583f;
      text-align: right;
    }

    .mood-remaining .remaining-count {
      font-weight: 700;
    }

    .mood-remaining .remaining-count.zero {
      color: #d64b43;
    }

    .mood-btn:disabled {
      opacity: 0.45;
      cursor: not-allowed;
      transform: none;
    }

    .mood-btn.recent {
      position: relative;
      transform: translateY(-2px) scale(1.02);
    }

    .mood-btn.recent .mood-color {
      position: relative;
      border: 1px solid rgba(255, 243, 221, 0.9);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.35),
        0 0 0 1px rgba(120, 83, 53, 0.22),
        0 8px 14px rgba(96, 75, 55, 0.32),
        0 2px 4px rgba(96, 75, 55, 0.24);
      transform-origin: center;
      animation: mood-recent-beat 1.45s cubic-bezier(0.22, 0.02, 0.2, 1) infinite;
    }

    .mood-btn.recent::before,
    .mood-btn.recent::after {
      content: "";
      position: absolute;
      pointer-events: none;
      z-index: 2;
    }

    .mood-btn.recent::before {
      right: 13px;
      top: 9px;
      width: 8px;
      height: 2.8px;
      background: #6a4a31;
      border-radius: 999px;
      transform: rotate(42deg);
      box-shadow: 0 1px 1px rgba(72, 53, 37, 0.42);
    }

    .mood-btn.recent::after {
      right: 6px;
      top: 6px;
      width: 13px;
      height: 2.8px;
      background: #6a4a31;
      border-radius: 999px;
      transform: rotate(-43deg);
      box-shadow:
        0 1px 1px rgba(72, 53, 37, 0.45),
        0 0 2px rgba(255, 247, 223, 0.34);
    }

    .mood-btn.recent .mood-label {
      font-weight: 700;
      color: #4f3b2b;
    }

    .mood-btn.recent:disabled {
      opacity: 0.86;
    }

    @keyframes mood-recent-beat {
      0%, 100% {
        transform: scale(1);
      }
      28% {
        transform: scale(1.16);
      }
      65% {
        transform: scale(1.03);
      }
    }

    .med-slot {
      margin: 0;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      border: 1px solid rgba(164, 136, 106, 0.38);
      background: rgba(255, 247, 236, 0.9);
      color: #674b32;
      font-size: 0.84rem;
      padding: 4px 10px;
      white-space: nowrap;
    }

    .med-slot-toggle {
      border: 1px solid rgba(164, 136, 106, 0.38);
      cursor: pointer;
      font-family: inherit;
      appearance: none;
      -webkit-appearance: none;
    }

    .med-slot-toggle:active {
      transform: scale(0.985);
    }

    .med-list {
      margin: 10px 0 0;
      padding: 0;
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: none;
      overflow: visible;
    }

    .med-item {
      position: relative;
      isolation: isolate;
      overflow: hidden;
      border-radius: 12px;
      border: 1px solid rgba(174, 144, 113, 0.28);
      background: rgba(255, 252, 247, 0.92);
      padding: 8px 10px 9px;
      color: #5f4935;
      font-size: 0.92rem;
    }

    .med-item.open {
      overflow: visible;
      z-index: 4;
    }

    .med-row {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      min-width: 0;
      position: relative;
    }

    .med-main {
      flex: 1;
      min-width: 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .med-label {
      flex: 1;
      min-width: 0;
      display: flex;
      align-items: center;
      gap: 6px;
      position: relative;
      transition: opacity 140ms ease;
    }

    .med-name {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .med-dots {
      flex: 1;
      min-width: 20px;
      height: 0;
      border-bottom: 2px dotted rgba(145, 118, 93, 0.55);
      opacity: 0.8;
      transform: translateY(1px);
    }

    .med-dose {
      white-space: nowrap;
      font-weight: 700;
      color: #6d5138;
    }

    .med-photo-btn {
      width: 36px;
      height: 36px;
      flex: 0 0 36px;
      border-radius: 8px;
      border: 1px solid rgba(170, 140, 108, 0.42);
      background: rgba(255, 249, 241, 0.9);
      box-shadow: 0 2px 4px rgba(101, 76, 49, 0.12);
      padding: 0;
      overflow: hidden;
      cursor: pointer;
      position: relative;
      transition: transform 120ms ease, box-shadow 160ms ease, border-color 160ms ease, background-color 160ms ease;
    }

    .med-photo-btn:active {
      transform: scale(0.97);
    }

    .med-item.open .med-photo-btn {
      border-color: rgba(152, 114, 80, 0.62);
      background: rgba(255, 249, 241, 0.92);
      box-shadow:
        0 3px 6px rgba(114, 78, 44, 0.14),
        0 0 0 1px rgba(176, 132, 92, 0.3) inset;
      transform: translateY(-1px) rotate(-2.2deg);
      overflow: visible;
      z-index: 6;
      border-radius: 9px;
    }

    .med-item.open .med-photo-btn::before {
      content: "";
      position: absolute;
      right: -6px;
      top: -6px;
      width: 11px;
      height: 11px;
      border-radius: 999px;
      background: radial-gradient(circle at 35% 35%, #fff7e8 0 28%, #dd8d5d 29% 100%);
      box-shadow: 0 3px 7px rgba(117, 66, 36, 0.4);
      pointer-events: none;
      z-index: 9;
      animation: med-photo-open-pin 0.56s cubic-bezier(0.33, 0.01, 0.2, 1) infinite alternate;
    }

    .med-item.open .med-photo-btn::after {
      content: "";
      position: absolute;
      left: -5px;
      top: -5px;
      right: -5px;
      bottom: -5px;
      border-radius: 11px;
      border: 1px solid rgba(145, 104, 68, 0.58);
      background:
        linear-gradient(90deg, rgba(220, 198, 170, 0.92), rgba(203, 173, 137, 0.9), rgba(220, 198, 170, 0.92)) top center / calc(100% - 12px) 5px no-repeat,
        linear-gradient(90deg, rgba(209, 181, 147, 0.9), rgba(191, 160, 124, 0.88), rgba(209, 181, 147, 0.9)) bottom center / calc(100% - 12px) 5px no-repeat,
        linear-gradient(0deg, rgba(214, 188, 154, 0.9), rgba(192, 161, 125, 0.9), rgba(214, 188, 154, 0.9)) left center / 5px calc(100% - 12px) no-repeat,
        linear-gradient(0deg, rgba(205, 177, 144, 0.9), rgba(183, 151, 118, 0.9), rgba(205, 177, 144, 0.9)) right center / 5px calc(100% - 12px) no-repeat,
        linear-gradient(145deg, rgba(255, 244, 227, 0.36), rgba(255, 244, 227, 0) 42%),
        linear-gradient(320deg, rgba(104, 76, 50, 0.16), rgba(104, 76, 50, 0) 56%);
      box-shadow:
        0 0 0 1px rgba(245, 225, 196, 0.74) inset,
        0 0 0 2.2px rgba(159, 119, 83, 0.3) inset,
        0 2px 5px rgba(94, 56, 29, 0.14);
      transform: rotate(-1.7deg);
      opacity: 0.9;
      z-index: 7;
      pointer-events: none;
      animation: med-photo-open-frame 2.1s ease-in-out infinite;
    }

    @keyframes med-photo-open-pin {
      0% {
        opacity: 0.78;
        transform: translateY(0) rotate(-6deg) scale(0.86);
      }
      100% {
        opacity: 1;
        transform: translateY(-1px) rotate(6deg) scale(1.2);
      }
    }

    @keyframes med-photo-open-frame {
      0%, 100% {
        opacity: 0.92;
        transform: rotate(-1.95deg) scale(0.996);
      }
      50% {
        opacity: 1;
        transform: rotate(-1.2deg) scale(1.008);
      }
    }

    .med-photo-btn img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
      border-radius: 7px;
    }

    .med-row::before,
    .med-row::after {
      content: "";
      position: absolute;
      top: 50%;
      height: 42px;
      width: var(--scribble-side-width, clamp(110px, 28%, 190px));
      pointer-events: none;
      z-index: 3;
      opacity: 0;
      transition: opacity 110ms ease;
      background-repeat: no-repeat;
      filter: saturate(1.14) contrast(1.08);
    }

    .med-row::before {
      width: var(--scribble-side-width, clamp(110px, 28%, 190px));
      left: 80px;
      transform: translate(-50%, -50%) rotate(var(--scribble-left-angle, -2.5deg));
      background-image: var(--scribble-left-pattern);
      background-size: var(--scribble-left-size, 100% 100%);
      background-position: 50% 50%;
    }

    .med-row::after {
      width: var(--scribble-right-width, clamp(78px, 18%, 128px));
      right: 75px;
      transform: translate(50%, -50%) rotate(var(--scribble-right-angle, 2.5deg));
      background-image: var(--scribble-right-pattern);
      background-size: var(--scribble-right-size, 100% 100%);
      background-position: 50% 50%;
    }

    .med-item.checked .med-row::before,
    .med-item.checked .med-row::after {
      opacity: 0.96;
    }

    .med-item input[type="checkbox"] {
      width: 17px;
      height: 17px;
      accent-color: #b26b44;
    }

    .med-detail {
      --postit-bg-top: rgba(255, 252, 204, 0.98);
      --postit-bg-bottom: rgba(252, 238, 162, 0.96);
      --postit-line: rgba(0, 0, 0, 0.03);
      --postit-border: rgba(184, 156, 90, 0.52);
      --postit-shadow-outer: rgba(117, 91, 43, 0.2);
      --postit-shadow-inset-top: rgba(255, 255, 255, 0.7);
      --postit-shadow-inset-bottom: rgba(173, 134, 56, 0.22);
      --postit-tape-top: rgba(247, 243, 229, 0.78);
      --postit-tape-bottom: rgba(228, 220, 195, 0.74);
      --postit-fold-main: rgba(221, 204, 121, 0.82);
      --postit-fold-shadow: rgba(172, 136, 70, 0.35);
      --postit-text: #604a2f;
      display: none;
      position: relative;
      margin-top: 10px;
      margin-left: 24px;
      margin-right: 2px;
      padding: 11px 12px 10px;
      border-radius: 2px 10px 3px 9px;
      border: 1px solid var(--postit-border);
      background:
        linear-gradient(180deg, var(--postit-bg-top), var(--postit-bg-bottom)),
        repeating-linear-gradient(180deg, var(--postit-line) 0 1px, rgba(0, 0, 0, 0) 1px 6px);
      box-shadow:
        0 4px 8px var(--postit-shadow-outer),
        0 1px 0 var(--postit-shadow-inset-top) inset,
        0 -1px 0 var(--postit-shadow-inset-bottom) inset;
      transform: rotate(-1.1deg);
      line-height: 1.5;
      color: var(--postit-text);
      white-space: pre-line;
    }

    .med-detail.postit-theme-yellow {
      --postit-bg-top: rgba(255, 252, 204, 0.98);
      --postit-bg-bottom: rgba(252, 238, 162, 0.96);
      --postit-border: rgba(184, 156, 90, 0.52);
      --postit-shadow-outer: rgba(117, 91, 43, 0.2);
      --postit-shadow-inset-bottom: rgba(173, 134, 56, 0.22);
      --postit-fold-main: rgba(221, 204, 121, 0.82);
      --postit-fold-shadow: rgba(172, 136, 70, 0.35);
      --postit-text: #604a2f;
    }

    .med-detail.postit-theme-peach {
      --postit-bg-top: rgba(255, 235, 210, 0.98);
      --postit-bg-bottom: rgba(247, 210, 176, 0.96);
      --postit-border: rgba(187, 133, 94, 0.5);
      --postit-shadow-outer: rgba(132, 88, 58, 0.2);
      --postit-shadow-inset-bottom: rgba(177, 120, 83, 0.22);
      --postit-tape-top: rgba(246, 236, 226, 0.8);
      --postit-tape-bottom: rgba(224, 206, 190, 0.74);
      --postit-fold-main: rgba(232, 184, 141, 0.84);
      --postit-fold-shadow: rgba(183, 124, 82, 0.36);
      --postit-text: #5f4531;
    }

    .med-detail.postit-theme-mint {
      --postit-bg-top: rgba(224, 248, 230, 0.98);
      --postit-bg-bottom: rgba(193, 235, 208, 0.96);
      --postit-border: rgba(120, 170, 138, 0.5);
      --postit-shadow-outer: rgba(75, 123, 95, 0.18);
      --postit-shadow-inset-bottom: rgba(95, 154, 119, 0.2);
      --postit-tape-top: rgba(236, 244, 236, 0.8);
      --postit-tape-bottom: rgba(206, 223, 210, 0.74);
      --postit-fold-main: rgba(156, 211, 178, 0.84);
      --postit-fold-shadow: rgba(91, 153, 120, 0.34);
      --postit-text: #375343;
    }

    .med-detail::before {
      content: "";
      position: absolute;
      top: -7px;
      left: 50%;
      width: 46px;
      height: 12px;
      transform: translateX(-50%) rotate(-3deg);
      border-radius: 3px;
      background:
        linear-gradient(180deg, var(--postit-tape-top), var(--postit-tape-bottom)),
        repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.14) 0 2px, rgba(0, 0, 0, 0.03) 2px 4px);
      box-shadow: 0 1px 2px rgba(98, 79, 44, 0.2);
      pointer-events: none;
    }

    .med-detail::after {
      content: "";
      position: absolute;
      top: -1px;
      right: -1px;
      width: 14px;
      height: 14px;
      background: linear-gradient(135deg, var(--postit-fold-main) 0 49%, var(--postit-fold-shadow) 50% 100%);
      clip-path: polygon(100% 0, 0 0, 100% 100%);
      pointer-events: none;
    }

    .med-item.open .med-detail {
      display: block;
      animation: med-detail-postit-in 240ms ease-out;
    }

    .med-detail p {
      margin: 0;
      font-size: 0.84rem;
    }

    .med-detail p + p {
      margin-top: 5px;
    }

    @keyframes med-detail-postit-in {
      0% {
        opacity: 0;
        transform: rotate(-2.1deg) translateY(-5px) scale(0.98);
      }
      100% {
        opacity: 1;
        transform: rotate(-1.1deg) translateY(0) scale(1);
      }
    }

    .meds-surface {
      height: auto;
      min-height: 0;
      overflow: visible;
    }

    .add-med-wrap {
      padding: 2px 0 0;
      display: flex;
      justify-content: center;
    }

    .add-med-toggle {
      text-decoration: none;
      color: var(--accent);
      font-size: 1rem;
      font-weight: 700;
      border-bottom: 2px dashed rgba(195, 104, 70, 0.72);
      padding-bottom: 2px;
    }

    .team-credit {
      width: max-content;
      margin: 4px auto calc(env(safe-area-inset-bottom, 0px) + 6px);
      color: rgba(96, 80, 64, 0.42);
      font-size: 0.62rem;
      letter-spacing: 0.01em;
      user-select: none;
      text-align: center;
    }

    .dday-modal {
      position: fixed;
      inset: 0;
      z-index: 1100;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 16px;
      background: rgba(60, 46, 33, 0.36);
    }

    .dday-modal.show {
      display: flex;
    }

    .dday-sheet {
      width: min(100%, 360px);
      border-radius: 18px;
      border: 1px solid rgba(176, 147, 117, 0.44);
      background: rgba(255, 250, 243, 0.98);
      box-shadow: 0 14px 26px rgba(98, 76, 52, 0.24);
      padding: 16px 14px 14px;
    }

    .dday-title {
      margin: 0;
      font-size: 1.05rem;
      color: #5b4330;
    }

    .dday-desc {
      margin: 8px 0 12px;
      font-size: 0.86rem;
      line-height: 1.45;
      color: #7a6a57;
    }

    .dday-input {
      width: 100%;
      border: 1px solid rgba(173, 142, 110, 0.44);
      border-radius: 12px;
      background: #fffdf8;
      min-height: 42px;
      padding: 8px 10px;
      font-size: 0.96rem;
      color: #5d4634;
      font-family: inherit;
    }

    #ddayInput {
      width: 156px;
      max-width: 100%;
      margin: 0 auto;
      display: block;
    }

    .dday-actions {
      margin-top: 12px;
      display: flex;
      gap: 8px;
    }

    .dday-btn {
      flex: 1;
      min-height: 40px;
      border-radius: 12px;
      border: 0;
      font-family: inherit;
      font-size: 0.92rem;
      font-weight: 700;
      cursor: pointer;
    }

    .dday-cancel {
      background: #efe2d1;
      color: #5b4432;
    }

    .dday-save {
      background: #f6dfd2;
      color: #8a4727;
    }

    .med-time-grid {
      margin-top: 8px;
      display: grid;
      gap: 8px;
      width: 100%;
      min-width: 0;
      overflow-x: hidden;
      justify-items: center;
    }

    .med-time-row {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      width: fit-content;
      min-width: 0;
    }

    .med-time-label {
      flex: 0 0 52px;
      font-size: 0.9rem;
      color: #6a4e36;
      font-weight: 700;
    }

    .med-time-row .dday-input {
      flex: 0 1 156px;
      width: 156px;
      min-width: 0;
      max-width: calc(100% - 56px);
      padding: 7px 8px;
      font-size: 0.9rem;
    }
  </style>
</head>
<body>
  <header class="top-bar" aria-label="고정 상단 바">
    <div class="top-logo" aria-label="로고 영역">LOGO</div>
    <p class="top-bar-text">메인 화면</p>
  </header>

  <main class="wrap">
    <section class="top-toggle-row" aria-label="상단 기능 토글">
      <a
        id="diaryToggle"
        class="top-toggle diary-toggle bookmarkable"
        href="/ui/diary"
        aria-label="일기 페이지로 이동"
        data-bookmark-key="diary"
      >
        <span class="toggle-illustration-wrap" aria-hidden="true">
          <img
            class="toggle-illustration"
            alt=""
            src="data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2064%2064%27%3E%3Cdefs%3E%3ClinearGradient%20id%3D%27cover%27%20x1%3D%270%27%20y1%3D%270%27%20x2%3D%271%27%20y2%3D%271%27%3E%3Cstop%20offset%3D%270%27%20stop-color%3D%27%239b6b45%27%2F%3E%3Cstop%20offset%3D%271%27%20stop-color%3D%27%236e472e%27%2F%3E%3C%2FlinearGradient%3E%3ClinearGradient%20id%3D%27label%27%20x1%3D%270%27%20y1%3D%270%27%20x2%3D%271%27%20y2%3D%271%27%3E%3Cstop%20offset%3D%270%27%20stop-color%3D%27%23efd8aa%27%2F%3E%3Cstop%20offset%3D%271%27%20stop-color%3D%27%23d1af75%27%2F%3E%3C%2FlinearGradient%3E%3ClinearGradient%20id%3D%27ribbon%27%20x1%3D%270%27%20y1%3D%270%27%20x2%3D%270%27%20y2%3D%271%27%3E%3Cstop%20offset%3D%270%27%20stop-color%3D%27%23d66a59%27%2F%3E%3Cstop%20offset%3D%271%27%20stop-color%3D%27%23b7473b%27%2F%3E%3C%2FlinearGradient%3E%3C%2Fdefs%3E%3Cpath%20d%3D%27M29.5%209v53.5l3.3-2.9%203.3%202.9V9z%27%20fill%3D%27url%28%23ribbon%29%27%20stroke%3D%27%238f3f36%27%20stroke-width%3D%270.8%27%2F%3E%3Crect%20x%3D%2713%27%20y%3D%277%27%20width%3D%2738%27%20height%3D%2750%27%20rx%3D%278%27%20fill%3D%27url%28%23cover%29%27%20stroke%3D%27%235d3d27%27%20stroke-width%3D%272%27%2F%3E%3Crect%20x%3D%2716.5%27%20y%3D%2710.5%27%20width%3D%276%27%20height%3D%2743%27%20rx%3D%273%27%20fill%3D%27%23c79a6f%27%20opacity%3D%270.96%27%2F%3E%3Crect%20x%3D%2726%27%20y%3D%2714%27%20width%3D%2720%27%20height%3D%2715%27%20rx%3D%273%27%20fill%3D%27url%28%23label%29%27%20stroke%3D%27%239b774d%27%20stroke-width%3D%271.2%27%2F%3E%3Cpath%20d%3D%27M30%2019.8h12%27%20stroke%3D%27%237d5b38%27%20stroke-width%3D%271.8%27%20stroke-linecap%3D%27round%27%2F%3E%3Cpath%20d%3D%27M30%2023.8h9%27%20stroke%3D%27%237d5b38%27%20stroke-width%3D%271.6%27%20stroke-linecap%3D%27round%27%2F%3E%3Cpath%20d%3D%27M27%2035h18M27%2041h18M27%2047h14%27%20stroke%3D%27%23d6c2a0%27%20stroke-width%3D%271.8%27%20stroke-linecap%3D%27round%27%20opacity%3D%270.9%27%2F%3E%3Cpath%20d%3D%27M28.6%2058h7.6%27%20stroke%3D%27rgba%2866%2C39%2C20%2C0.24%29%27%20stroke-width%3D%270.85%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E"
          />
        </span>
        <span class="toggle-label">일기</span>
      </a>
      <button id="ddayToggle" class="top-toggle dday-toggle" type="button" aria-label="진료 D-Day 설정">
        <span id="ddayMeta" class="dday-meta">__INITIAL_DDAY_META__</span>
        <strong id="ddayValue" class="dday-value">
          <span class="dday-prefix">__INITIAL_DDAY_PREFIX__</span><span class="dday-number __INITIAL_DDAY_CLASS__">__INITIAL_DDAY_NUMBER__</span>
        </strong>
      </button>
      <a
        id="myInfoToggle"
        class="top-toggle bookmarkable"
        href="/ui/mypage"
        aria-label="내 정보 페이지로 이동"
        data-bookmark-key="myinfo"
      >
        <span class="toggle-illustration-wrap" aria-hidden="true">
          <img
            class="toggle-illustration"
            alt=""
            src="data:image/svg+xml,%3Csvg%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%20viewBox%3D%270%200%2064%2064%27%3E%3Cdefs%3E%3ClinearGradient%20id%3D%27bg%27%20x1%3D%270%27%20y1%3D%270%27%20x2%3D%271%27%20y2%3D%271%27%3E%3Cstop%20offset%3D%270%27%20stop-color%3D%27%23f7ead8%27%2F%3E%3Cstop%20offset%3D%271%27%20stop-color%3D%27%23ead0b0%27%2F%3E%3C%2FlinearGradient%3E%3ClinearGradient%20id%3D%27skin%27%20x1%3D%270%27%20y1%3D%270%27%20x2%3D%270%27%20y2%3D%271%27%3E%3Cstop%20offset%3D%270%27%20stop-color%3D%27%23f8e8d5%27%2F%3E%3Cstop%20offset%3D%271%27%20stop-color%3D%27%23eed5b8%27%2F%3E%3C%2FlinearGradient%3E%3C%2Fdefs%3E%3Crect%20x%3D%2710%27%20y%3D%278%27%20width%3D%2744%27%20height%3D%2748%27%20rx%3D%2710%27%20fill%3D%27url%28%23bg%29%27%20stroke%3D%27%23b88f64%27%20stroke-width%3D%271.8%27%2F%3E%3Cpath%20d%3D%27M15.2%2051.2c0-9.4%207.6-17.2%2016.8-17.2s16.8%207.8%2016.8%2017.2%27%20fill%3D%27url%28%23skin%29%27%20stroke%3D%27%238b6544%27%20stroke-width%3D%272.2%27%20stroke-linecap%3D%27round%27%2F%3E%3Ccircle%20cx%3D%2732%27%20cy%3D%2723.8%27%20r%3D%2711.2%27%20fill%3D%27url%28%23skin%29%27%20stroke%3D%27%238b6544%27%20stroke-width%3D%272.2%27%2F%3E%3Ccircle%20cx%3D%2727.7%27%20cy%3D%2722.5%27%20r%3D%271.2%27%20fill%3D%27%23694a32%27%2F%3E%3Ccircle%20cx%3D%2736.3%27%20cy%3D%2722.5%27%20r%3D%271.2%27%20fill%3D%27%23694a32%27%2F%3E%3Cpath%20d%3D%27M27.2%2028.1c1.2%201.4%202.8%202%204.8%202s3.6-.6%204.8-2%27%20fill%3D%27none%27%20stroke%3D%27%23694a32%27%20stroke-width%3D%271.8%27%20stroke-linecap%3D%27round%27%2F%3E%3C%2Fsvg%3E"
          />
        </span>
        <span class="toggle-label">내 정보</span>
      </a>
    </section>

    <section class="note-surface friend-surface">
      <div class="friend-fabric-noise" aria-hidden="true"></div>
      <div id="friendToyBall" class="friend-toy ball" role="button" tabindex="0" aria-label="장난감 공"></div>
      <div id="friendToyBone" class="friend-toy bone" role="button" tabindex="0" aria-label="장난감 뼈다귀"></div>
      <div id="toySecretNote" class="toy-secret-note" aria-live="polite"></div>
      <div
        id="friendNameplate"
        class="friend-nameplate"
        aria-live="polite"
        role="button"
        tabindex="0"
        aria-pressed="true"
        aria-label="이름표 흔들림 애니메이션 켜기/끄기"
      >__INITIAL_FRIEND_NAME__</div>
      <div id="friendBubble" class="friend-bubble" role="status" aria-live="polite">오늘은 어떤 이야기부터 해볼까?</div>
      <button id="friendToggle" class="friend-toggle" type="button" aria-label="내 친구 챗봇으로 이동">
        <div class="friend-image-wrap">
          <img id="friendImage" class="friend-image" src="__INITIAL_FRIEND_IMAGE__" alt="내 친구 이미지" />
        </div>
      </button>
    </section>

    <section class="note-surface mood-surface spring-note">
      <h2 class="section-title">오늘의 기분 선택 (7단계)</h2>
      <p id="moodRemaining" class="mood-remaining" aria-live="polite"></p>
      <div id="moodGrid" class="mood-grid" role="group" aria-label="오늘의 기분">
        <button type="button" class="mood-btn" aria-label="매우 기쁨"><span class="mood-color" style="--mood-color:#e73a35;--mood-face-color:#fff8ef"><span class="mood-face-art" aria-hidden="true"></span></span></button>
        <button type="button" class="mood-btn" aria-label="기쁨"><span class="mood-color" style="--mood-color:#ec6a3b;--mood-face-color:#fff8ef"><span class="mood-face-art" aria-hidden="true"></span></span></button>
        <button type="button" class="mood-btn" aria-label="약간 좋음"><span class="mood-color" style="--mood-color:#f19a4a;--mood-face-color:#fff8ef"><span class="mood-face-art" aria-hidden="true"></span></span></button>
        <button type="button" class="mood-btn" aria-label="보통"><span class="mood-color" style="--mood-color:#f2c66a;--mood-face-color:#5a3f2c"><span class="mood-face-art" aria-hidden="true"></span></span></button>
        <button type="button" class="mood-btn" aria-label="약간 우울"><span class="mood-color" style="--mood-color:#90bde3;--mood-face-color:#22496e"><span class="mood-face-art" aria-hidden="true"></span></span></button>
        <button type="button" class="mood-btn" aria-label="우울"><span class="mood-color" style="--mood-color:#5b8fcc;--mood-face-color:#eef6ff"><span class="mood-face-art" aria-hidden="true"></span></span></button>
        <button type="button" class="mood-btn" aria-label="매우 우울"><span class="mood-color" style="--mood-color:#2e67b1;--mood-face-color:#eef6ff"><span class="mood-face-art" aria-hidden="true"></span></span></button>
      </div>
      <p class="mood-help">마음 색을 고르면, 오늘 일기에 스티커로 남겨줄게요.</p>
    </section>

    <section class="note-surface meds-surface spring-note">
      <div class="med-head">
        <h2 id="medListTitle" class="section-title">복용약 리스트</h2>
        <button id="medSlot" class="med-slot med-slot-toggle" type="button" aria-label="복용 시간 기준 설정"></button>
      </div>
      <ul id="medList" class="med-list">
        <li class="med-item">
          <div class="med-row">
            <div class="med-main">
              <input id="med_fallback_1" type="checkbox" />
              <label class="med-label" for="med_fallback_1">
                <span class="med-name">임시 복용약 A</span>
                <span class="med-dots" aria-hidden="true"></span>
                <span class="med-dose">1정</span>
              </label>
            </div>
          </div>
        </li>
        <li class="med-item">
          <div class="med-row">
            <div class="med-main">
              <input id="med_fallback_2" type="checkbox" />
              <label class="med-label" for="med_fallback_2">
                <span class="med-name">임시 복용약 B</span>
                <span class="med-dots" aria-hidden="true"></span>
                <span class="med-dose">0.5정</span>
              </label>
            </div>
          </div>
        </li>
        <li class="med-item">
          <div class="med-row">
            <div class="med-main">
              <input id="med_fallback_3" type="checkbox" />
              <label class="med-label" for="med_fallback_3">
                <span class="med-name">임시 복용약 C</span>
                <span class="med-dots" aria-hidden="true"></span>
                <span class="med-dose">2정</span>
              </label>
            </div>
          </div>
        </li>
        <li class="med-item">
          <div class="med-row">
            <div class="med-main">
              <input id="med_fallback_4" type="checkbox" />
              <label class="med-label" for="med_fallback_4">
                <span class="med-name">임시 복용약 D</span>
                <span class="med-dots" aria-hidden="true"></span>
                <span class="med-dose">1.5정</span>
              </label>
            </div>
          </div>
        </li>
        <li class="med-item">
          <div class="med-row">
            <div class="med-main">
              <input id="med_fallback_5" type="checkbox" />
              <label class="med-label" for="med_fallback_5">
                <span class="med-name">임시 복용약 E</span>
                <span class="med-dots" aria-hidden="true"></span>
                <span class="med-dose">0.25정</span>
              </label>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <div class="add-med-wrap">
      <a class="add-med-toggle" href="/ui/medications/add">+ 복용약 추가하기</a>
    </div>
  </main>

  <div id="ddayModal" class="dday-modal" role="dialog" aria-modal="true" aria-labelledby="ddayTitle">
    <div class="dday-sheet">
      <h2 id="ddayTitle" class="dday-title">다음 진료일 설정</h2>
      <p class="dday-desc">날짜를 선택하면 D-Day가 바로 갱신돼요.</p>
      <input id="ddayInput" class="dday-input" type="date" />
      <div class="dday-actions">
        <button id="ddayCancelBtn" class="dday-btn dday-cancel" type="button">취소</button>
        <button id="ddaySaveBtn" class="dday-btn dday-save" type="button">적용</button>
      </div>
    </div>
  </div>

  <div id="medTimeModal" class="dday-modal" role="dialog" aria-modal="true" aria-labelledby="medTimeTitle">
    <div class="dday-sheet">
      <h2 id="medTimeTitle" class="dday-title">복용 기준 시간 설정</h2>
      <p class="dday-desc">아침, 점심, 저녁 기준 시간을 원하는 대로 바꿀 수 있어요.</p>
      <div class="med-time-grid">
        <label class="med-time-row" for="morningTimeInput">
          <span class="med-time-label">아침</span>
          <input id="morningTimeInput" class="dday-input" type="time" />
        </label>
        <label class="med-time-row" for="lunchTimeInput">
          <span class="med-time-label">점심</span>
          <input id="lunchTimeInput" class="dday-input" type="time" />
        </label>
        <label class="med-time-row" for="eveningTimeInput">
          <span class="med-time-label">저녁</span>
          <input id="eveningTimeInput" class="dday-input" type="time" />
        </label>
      </div>
      <div class="dday-actions">
        <button id="medTimeCancelBtn" class="dday-btn dday-cancel" type="button">취소</button>
        <button id="medTimeSaveBtn" class="dday-btn dday-save" type="button">저장</button>
      </div>
    </div>
  </div>

  <div class="team-credit">Copyright 2026 5FCV. All rights reserved.</div>

  <script>
    const userId = "1";

    const moodLevels = [
      { id: "mood_1", label: "매우 기쁨", color: "#e73a35", sticker: "very_happy", faceColor: "#fff8ef" },
      { id: "mood_2", label: "기쁨", color: "#ec6a3b", sticker: "happy", faceColor: "#fff8ef" },
      { id: "mood_3", label: "약간 좋음", color: "#f19a4a", sticker: "slightly_good", faceColor: "#fff8ef" },
      { id: "mood_4", label: "보통", color: "#f2c66a", sticker: "neutral", faceColor: "#5a3f2c" },
      { id: "mood_5", label: "약간 우울", color: "#90bde3", sticker: "slightly_low", faceColor: "#22496e" },
      { id: "mood_6", label: "우울", color: "#5b8fcc", sticker: "sad", faceColor: "#eef6ff" },
      { id: "mood_7", label: "매우 우울", color: "#2e67b1", sticker: "very_sad", faceColor: "#eef6ff" }
    ];

    const chatBubbleByCharacter = {
      "참깨": [
        "놀 준비 완료!\\n나 눌러서 같이 수다 떨자 ♬",
        "지금 이야기하면 더 재밌을걸?\\n톡 하러 와!",
        "헤헤, 궁금한 거 있어?\\n나를 눌러 바로 말해줘!",
        "킥킥 😜 오늘 비밀 작전할래?\\n눌러서 작전회의 시작!",
        "장난꾸러기 참깨 출동! 🐾\\n지금 바로 말 걸어줘~",
        "심심하면 큰일이야! 🤭\\n나랑 떠들러 들어오자!",
        "딱 1분만 얘기해도 웃길 자신 있어 😎\\n톡 하러 와!",
        "오늘 텐션 올려줄게 🎉\\n나 눌러서 시작하자!"
      ],
      "들깨": [
        "천천히 얘기해도 괜찮아.\\n나를 눌러 이야기해줄래?",
        "오늘 마음, 내가 들어줄게.\\n톡으로 같이 정리하자.",
        "괜찮아, 여기 있어.\\n나를 눌러 대화 시작해보자.",
        "마음이 복잡해도 괜찮아 🌷\\n내가 옆에서 들어줄게.",
        "오늘 하루, 많이 애썼지? 🤍\\n편하게 말해줘.",
        "급하지 않아 🙂\\n천천히 이야기해도 돼.",
        "걱정되는 게 있다면\\n나랑 하나씩 풀어보자 🫶",
        "네 속도에 맞춰서 갈게 🍀\\n눌러서 이야기 시작하자."
      ],
      "통깨": [
        "우와, 지금 기분 궁금해!\\n나 눌러서 바로 얘기하자!",
        "오늘도 반응 준비 완료!\\n톡 열어서 같이 수다 떨자 ♡",
        "말 걸어주면 완전 좋아!\\n나를 눌러 챗봇으로 와!",
        "헉 진짜?! 😆 그 얘기 더 해줘!\\n바로 들어가자!",
        "리액션 풀충전 완료 ✨\\n나랑 톡하면 심심할 틈 0!",
        "와아아 궁금해 궁금해 🐶💫\\n눌러서 지금 얘기하자!",
        "네 한마디 기다리는 중 👀\\n어서 와서 말해줘!",
        "공감 버튼 연타 준비됐어 💛\\n채팅 열고 만나자!"
      ],
      "흑깨": [
        "필요한 이야기부터 차근차근.\\n나를 눌러 시작해보자.",
        "지금부터 함께 정리해보자.\\n톡으로 한 단계씩 가볼까?",
        "편하게 말해줘.\\n나를 누르면 바로 대화할 수 있어.",
        "복잡한 건 내가 순서대로 도와줄게 📘\\n차분히 시작하자.",
        "지금 필요한 것부터 체크해보자 ✅\\n눌러서 같이 정리하자.",
        "한 번에 다 하지 않아도 돼 🙂\\n하나씩 같이 보자.",
        "막막하면 기준부터 세우면 돼 🧩\\n내가 옆에서 도와줄게.",
        "천천히 설명해줄게 🤝\\n채팅에서 바로 시작하자."
      ]
    };

    const chatBubbleCommon = [
      "지금 바로 이야기하자.\\n나를 눌러 챗봇으로 와!",
      "오늘 생각, 들려줘.\\n톡에서 기다리고 있어.",
      "한마디부터 시작해볼까?\\n눌러서 대화 열기!",
      "네 이야기 듣고 싶어 😊\\n지금 바로 들어와!",
      "톡 한 번이면 충분해 💬\\n눌러서 시작하자!",
      "잠깐 들러도 좋아 🌼\\n내가 기다리고 있어!"
    ];

    const DAILY_MOOD_STICKER_LIMIT = 4;
    const DEFAULT_MED_SCHEDULE = {
      morning: "06:00",
      lunch: "11:00",
      evening: "17:00"
    };
    const stateCache = {
      uiPreferences: null,
      visitSchedule: { next_visit_date: "__INITIAL_VISIT_DATE__" || null },
      medicationSchedule: { ...DEFAULT_MED_SCHEDULE },
      moodByDate: new Map(),
      moodRemainingByDate: new Map()
    };

    function apiHeaders(extra = {}) {
      return { "X-User-Id": userId, ...extra };
    }

    async function apiJson(url, options = {}) {
      const headers = { ...apiHeaders(), ...(options.headers || {}) };
      const requestInit = { ...options, headers };
      if (requestInit.body && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
      }
      const response = await fetch(url, requestInit);
      if (response.status === 204) return null;
      let data = null;
      try {
        data = await response.json();
      } catch (_error) {
        data = null;
      }
      if (!response.ok) {
        const detail = (data && data.detail) ? data.detail : `HTTP ${response.status}`;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      return data;
    }

    function pickRandom(list) {
      if (!list || list.length === 0) return "";
      return list[Math.floor(Math.random() * list.length)];
    }

    function pickRandomPostitThemeClass() {
      const themes = ["postit-theme-yellow", "postit-theme-peach", "postit-theme-mint"];
      return pickRandom(themes) || "postit-theme-yellow";
    }

    function getChatBubbleText(characterId) {
      const specific = chatBubbleByCharacter[characterId] || [];
      const useSpecific = specific.length > 0 && Math.random() < 0.85;
      return useSpecific ? pickRandom(specific) : pickRandom(chatBubbleCommon);
    }

    function buildChatbotImageCandidates(characterId, apiImageUrl) {
      const byCharacter = {
        "참깨": {
          removebg: "/static/characters/chamkkae-removebg.png",
          origin: "/static/characters/chamkkae.jpeg"
        },
        "들깨": {
          removebg: "/static/characters/deulkkae-removebg.png",
          origin: "/static/characters/deulkkae.jpeg"
        },
        "통깨": {
          removebg: "/static/characters/tongkkae-removebg.png",
          origin: "/static/characters/tongkkae.jpeg"
        },
        "흑깨": {
          removebg: "/static/characters/heukkkae-removebg.png",
          origin: "/static/characters/heukkkae.jpeg"
        }
      };

      const candidates = [];
      const push = (url) => {
        if (!url) return;
        if (!candidates.includes(url)) candidates.push(url);
      };

      if (apiImageUrl) {
        push(apiImageUrl.replace(/\\.(png|jpe?g|webp)(\\?.*)?$/i, "-removebg.png"));
        push(apiImageUrl);
      }

      if (characterId && byCharacter[characterId]) {
        push(byCharacter[characterId].removebg);
        push(byCharacter[characterId].origin);
      }

      push("/static/characters/chamkkae-removebg.png");
      push("/static/characters/chamkkae.jpeg");

      return candidates;
    }

    function setImageWithFallback(imageEl, candidates, altText) {
      let index = 0;
      const list = (Array.isArray(candidates) ? candidates : []).filter(Boolean);
      if (list.length === 0) return;

      imageEl.alt = altText || "친구 이미지";
      imageEl.onerror = () => {
        index += 1;
        if (index < list.length) {
          imageEl.src = list[index];
        } else {
          imageEl.onerror = null;
        }
      };
      imageEl.src = list[0];
    }

    function parseTimeToMinutes(timeStr) {
      const m = /^([01]\\d|2[0-3]):([0-5]\\d)$/.exec(String(timeStr || ""));
      if (!m) return null;
      return Number(m[1]) * 60 + Number(m[2]);
    }

    function formatToAmPm(timeStr) {
      const minutes = parseTimeToMinutes(timeStr);
      if (minutes === null) return "AM 00:00";
      const hour24 = Math.floor(minutes / 60);
      const min = String(minutes % 60).padStart(2, "0");
      const isPm = hour24 >= 12;
      const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12;
      return `${isPm ? "PM" : "AM"} ${String(hour12).padStart(2, "0")}:${min}`;
    }

    function normalizeMedicationSchedule(schedule) {
      const src = schedule && typeof schedule === "object" ? schedule : {};
      return {
        morning: String(src.morning_time || src.morning || DEFAULT_MED_SCHEDULE.morning),
        lunch: String(src.lunch_time || src.lunch || DEFAULT_MED_SCHEDULE.lunch),
        evening: String(src.evening_time || src.evening || DEFAULT_MED_SCHEDULE.evening)
      };
    }

    function getMedicationSchedule() {
      return { ...stateCache.medicationSchedule };
    }

    async function fetchMedicationSchedule() {
      const saved = await apiJson("/api/v1/main/me/medication-schedule");
      stateCache.medicationSchedule = normalizeMedicationSchedule(saved || {});
      return getMedicationSchedule();
    }

    async function saveMedicationSchedule(schedule) {
      const saved = await apiJson("/api/v1/main/me/medication-schedule", {
        method: "PUT",
        body: JSON.stringify({
          morning_time: schedule.morning,
          lunch_time: schedule.lunch,
          evening_time: schedule.evening
        })
      });
      stateCache.medicationSchedule = normalizeMedicationSchedule(saved || schedule);
      return getMedicationSchedule();
    }

    function isValidMedicationSchedule(schedule) {
      const m = parseTimeToMinutes(schedule.morning);
      const l = parseTimeToMinutes(schedule.lunch);
      const e = parseTimeToMinutes(schedule.evening);
      if (m === null || l === null || e === null) return false;
      return m < l && l < e;
    }

    async function getMedicationPlans(targetDateISO) {
      const query = targetDateISO ? `?target_date=${encodeURIComponent(targetDateISO)}` : "";
      const parsed = await apiJson("/api/v1/main/me/medication-plans" + query);
      return Array.isArray(parsed) ? parsed : [];
    }

    function getSlotsByTimesPerDay(timesPerDay) {
      if (timesPerDay >= 3) return ["morning", "lunch", "evening"];
      if (timesPerDay === 2) return ["morning", "evening"];
      return ["morning"];
    }

    function isMedicationActiveOnDate(plan, targetDateISO) {
      const start = toMidnight(new Date(`${plan.start_date}T00:00:00`));
      const target = toMidnight(new Date(`${targetDateISO}T00:00:00`));
      if (Number.isNaN(start.getTime()) || Number.isNaN(target.getTime())) return false;
      const diffDays = Math.floor((target - start) / 86400000);
      return diffDays >= 0 && diffDays < plan.total_days;
    }

    async function getMedicationsForSlot(slotKey, targetDateISO) {
      const plans = await getMedicationPlans(targetDateISO);
      return plans
        .filter((plan) => isMedicationActiveOnDate(plan, targetDateISO))
        .filter((plan) => getSlotsByTimesPerDay(plan.times_per_day).includes(slotKey))
        .map((plan) => ({
          id: plan.id,
          name: plan.name,
          dose: plan.dose_per_take,
          times_per_day: plan.times_per_day,
          total_days: plan.total_days,
          start_date: plan.start_date,
          medicine_image_url: plan.medicine_image_url || "",
          medicine_effect_summary: plan.medicine_effect_summary || ""
        }));
    }

    function formatDoseText(doseValue) {
      const n = Math.round((Number(doseValue) || 1) * 100) / 100;
      const text = Number.isInteger(n)
        ? String(n)
        : String(n).replace(/\\.0+$/, "").replace(/(\\.\\d*?)0+$/, "$1");
      return `${text}정`;
    }

    function formatCountText(value) {
      const n = Math.round((Number(value) || 0) * 100) / 100;
      if (Number.isInteger(n)) return String(n);
      return String(n).replace(/\\.0+$/, "").replace(/(\\.\\d*?)0+$/, "$1");
    }

    function calculateRemainingMedicationDays(startDateISO, totalDays, referenceDateISO) {
      const total = Math.max(0, Number(totalDays) || 0);
      if (!startDateISO || total <= 0) return 0;
      const start = toMidnight(new Date(`${startDateISO}T00:00:00`));
      const ref = toMidnight(new Date(`${referenceDateISO}T00:00:00`));
      if (Number.isNaN(start.getTime()) || Number.isNaN(ref.getTime())) return total;
      const passedDays = Math.max(0, Math.floor((ref - start) / 86400000));
      return Math.max(0, total - passedDays);
    }

    function getMedicationFallbackImageDataUri() {
      return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 56 56'%3E%3Crect width='56' height='56' rx='10' fill='%23fff6ea'/%3E%3Cg transform='translate(8,10) rotate(-12 20 18)'%3E%3Crect x='4' y='10' width='32' height='16' rx='8' fill='%23f7d79f' stroke='%23c99652' stroke-width='1.5'/%3E%3Cpath d='M20 10v16' stroke='%23c99652' stroke-width='1.5'/%3E%3Crect x='12' y='13' width='8' height='10' rx='4' fill='%23fff8ee' opacity='0.9'/%3E%3C/g%3E%3C/svg%3E";
    }

    function getMedicationDisplayImage(url) {
      const clean = String(url || "").trim();
      return clean || getMedicationFallbackImageDataUri();
    }

    async function readDailyMoodStickers(date) {
      if (stateCache.moodByDate.has(date)) {
        return stateCache.moodByDate.get(date);
      }
      const rows = await apiJson(`/api/v1/main/me/mood-stickers?mood_date=${encodeURIComponent(date)}`);
      const items = Array.isArray(rows) ? rows : [];
      stateCache.moodByDate.set(date, items);
      return items;
    }

    async function createDailyMoodSticker(item) {
      const payload = {
        mood_date: item.date,
        mood_id: item.mood_id,
        mood_label: item.mood_label,
        mood_sticker: item.mood_sticker,
        saved_at: item.saved_at
      };
      const saved = await apiJson("/api/v1/main/me/mood-stickers", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      const rows = await readDailyMoodStickers(item.date);
      const next = [...rows, saved].slice(0, DAILY_MOOD_STICKER_LIMIT);
      stateCache.moodByDate.set(item.date, next);
      return next;
    }

    function buildDiaryParams(date, selectedMood, stickers) {
      const labels = stickers.map((item) => item.mood_label || "").filter(Boolean);
      const stickerCodes = stickers.map((item) => item.mood_sticker || "").filter(Boolean);
      const params = new URLSearchParams({
        date,
        mood_count: String(stickers.length),
        labels: labels.join(","),
        stickers: stickerCodes.join(","),
      });

      if (selectedMood) {
        params.set("mood", selectedMood.id);
        params.set("label", selectedMood.label);
        params.set("sticker", selectedMood.sticker);
      }
      return params;
    }

    async function updateMoodRemainingInfo(date) {
      const result = await apiJson(`/api/v1/main/me/mood-stickers/remaining?mood_date=${encodeURIComponent(date)}`);
      const used = Number((result && result.used) || 0);
      const limit = Number((result && result.limit) || DAILY_MOOD_STICKER_LIMIT);
      const remaining = Math.max(0, limit - used);
      stateCache.moodRemainingByDate.set(date, { used, limit, remaining });
      const el = document.getElementById("moodRemaining");
      if (el) {
        const countClass = remaining === 0 ? "remaining-count zero" : "remaining-count";
        el.innerHTML =
          `오늘 남은 스티커: <span class="${countClass}">${remaining}</span>/${limit}`;
      }
      return remaining;
    }

    function formatMoodToggleLabel(label) {
      const compact = String(label || "").replace(/\\s+/g, "");
      if (compact.length === 4) {
        return `${compact.slice(0, 2)}<br>${compact.slice(2)}`;
      }
      return String(label || "");
    }

    function getMoodFaceSvgMarkup(moodId, strokeColor) {
      const color = String(strokeColor || "#fff8ef");
      let eyes = `<circle cx="8.2" cy="8.8" r="1.2" fill="${color}"/><circle cx="15.8" cy="8.8" r="1.2" fill="${color}"/>`;
      let mouth = `<path d="M7.3 14.2 Q12 16.1 16.7 14.2" stroke="${color}" stroke-width="2.1" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
      let extra = "";

      if (moodId === "mood_1") {
        eyes = `<circle cx="8.2" cy="8.5" r="1.35" fill="${color}"/><circle cx="15.8" cy="8.5" r="1.35" fill="${color}"/>`;
        mouth = `<path d="M6.2 12.6 Q12 18.6 17.8 12.6" stroke="${color}" stroke-width="2.35" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
        extra = `<path d="M2.3 5.2 L3.4 3.1 L4.5 5.2 L6.6 6.3 L4.5 7.4 L3.4 9.5 L2.3 7.4 L0.2 6.3 Z" fill="${color}" opacity="0.88"/><path d="M19.5 4.3 L20.5 2.4 L21.5 4.3 L23.4 5.3 L21.5 6.3 L20.5 8.2 L19.5 6.3 L17.6 5.3 Z" fill="${color}" opacity="0.86"/>`;
      } else if (moodId === "mood_2") {
        eyes = `<circle cx="8.1" cy="8.3" r="1.35" fill="${color}"/><circle cx="15.9" cy="8.3" r="1.35" fill="${color}"/><path d="M6 6.8 Q8.1 5.7 10.2 6.8" stroke="${color}" stroke-width="1.75" fill="none" stroke-linecap="round"/><path d="M13.8 6.8 Q15.9 5.7 18 6.8" stroke="${color}" stroke-width="1.75" fill="none" stroke-linecap="round"/>`;
        mouth = `<path d="M6.2 12.4 Q12 19.2 17.8 12.4" stroke="${color}" stroke-width="2.45" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path d="M8.3 13.9 Q12 16.9 15.7 13.9" stroke="${color}" stroke-width="1.65" fill="none" stroke-linecap="round" opacity="0.86"/>`;
        extra = `<path d="M2.8 8.2 L3.6 6.8 L4.4 8.2 L5.8 9 L4.4 9.8 L3.6 11.2 L2.8 9.8 L1.4 9 Z" fill="${color}" opacity="0.82"/>`;
      } else if (moodId === "mood_3") {
        eyes = `<circle cx="8.2" cy="8.9" r="1.1" fill="${color}"/><circle cx="15.8" cy="8.9" r="1.1" fill="${color}"/>`;
        mouth = `<path d="M7.6 14.3 Q12 16.2 16.4 14.3" stroke="${color}" stroke-width="1.9" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
      } else if (moodId === "mood_4") {
        eyes = `<circle cx="8.2" cy="9" r="1.03" fill="${color}"/><circle cx="15.8" cy="9" r="1.03" fill="${color}"/>`;
        mouth = `<path d="M8.2 14.9 Q12 15.4 15.8 14.9" stroke="${color}" stroke-width="1.75" fill="none" stroke-linecap="round"/>`;
      } else if (moodId === "mood_5") {
        eyes = `<path d="M6.8 8.4 Q8.2 7.6 9.6 8.4" stroke="${color}" stroke-width="1.75" fill="none" stroke-linecap="round"/><path d="M14.4 8.4 Q15.8 7.6 17.2 8.4" stroke="${color}" stroke-width="1.75" fill="none" stroke-linecap="round"/><circle cx="8.2" cy="9.8" r="1.05" fill="${color}"/><circle cx="15.8" cy="9.8" r="1.05" fill="${color}"/>`;
        mouth = `<path d="M7.2 15.3 Q12 13.1 16.8 15.3" stroke="${color}" stroke-width="2.0" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
      } else if (moodId === "mood_6") {
        eyes = `<path d="M6.7 8.7 Q8.2 7.8 9.7 8.7" stroke="${color}" stroke-width="1.8" fill="none" stroke-linecap="round"/><path d="M14.3 8.7 Q15.8 7.8 17.3 8.7" stroke="${color}" stroke-width="1.8" fill="none" stroke-linecap="round"/><circle cx="8.2" cy="10.1" r="1.03" fill="${color}"/><circle cx="15.8" cy="10.1" r="1.03" fill="${color}"/>`;
        mouth = `<path d="M6.9 15.9 Q12 12.9 17.1 15.9" stroke="${color}" stroke-width="2.15" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
        extra = `<path d="M18.6 11.2 C19.8 12.4 19.8 13.6 18.6 14.8 C17.4 13.6 17.4 12.4 18.6 11.2 Z" fill="${color}" opacity="0.86"/>`;
      } else if (moodId === "mood_7") {
        eyes = `<path d="M6.6 8.9 Q8.2 7.8 9.8 8.9" stroke="${color}" stroke-width="1.9" fill="none" stroke-linecap="round"/><path d="M14.2 8.9 Q15.8 7.8 17.4 8.9" stroke="${color}" stroke-width="1.9" fill="none" stroke-linecap="round"/><circle cx="8.2" cy="10.3" r="1.02" fill="${color}"/><circle cx="15.8" cy="10.3" r="1.02" fill="${color}"/>`;
        mouth = `<path d="M6.6 16.3 Q12 11.9 17.4 16.3" stroke="${color}" stroke-width="2.3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
        extra = `<path d="M18.4 11.3 C19.6 12.5 19.6 13.8 18.4 15 C17.2 13.8 17.2 12.5 18.4 11.3 Z" fill="${color}" opacity="0.86"/><path d="M5.6 11.3 C6.8 12.5 6.8 13.8 5.6 15 C4.4 13.8 4.4 12.5 5.6 11.3 Z" fill="${color}" opacity="0.86"/>`;
      }

      return `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">${eyes}${mouth}${extra}</svg>`;
    }

    function hashText(text) {
      let h = 0;
      const s = String(text || "");
      for (let i = 0; i < s.length; i += 1) {
        h = ((h << 5) - h) + s.charCodeAt(i);
        h |= 0;
      }
      return Math.abs(h);
    }

    function makeScribbleDataUri(pathD, strokeColor, strokeWidth) {
      const svg =
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 72">` +
        `<path d="${pathD}" fill="none" stroke="${strokeColor}" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round"/>` +
        `</svg>`;
      return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
    }

    function getRandomScribblePairStyle(seedText) {
      const colors = ["#7a2f86", "#9a3a4a", "#2f7a55", "#4a3a2a", "#cf8a35", "#5b93b3"];
      const paths = [
        "M8 58 L24 12 L40 60 L56 11 L72 58 L88 13 L104 59 L120 11 L136 58 L152 12 L168 59 L184 10 L200 58 L216 12 L232 56",
        "M8 46 C18 22 32 12 48 30 C63 48 43 60 26 50 C12 42 12 22 30 14 C46 8 68 14 78 30 C88 46 74 58 54 52 C34 46 34 26 52 18 C72 10 96 16 108 32 C120 48 104 58 82 52 C62 46 62 26 80 18 C100 10 128 16 140 32 C152 48 136 58 114 52 C94 46 94 26 112 18 C132 10 160 16 172 32 C184 48 168 58 146 52 C126 46 126 26 144 18 C164 10 192 16 204 32 C216 48 200 58 178 52",
        "M8 12 L20 58 L32 10 L44 60 L56 11 L68 59 L80 12 L92 58 L104 10 L116 60 L128 12 L140 58 L152 11 L164 59 L176 12 L188 58 L200 11 L212 60 L224 12 L236 56",
        "M8 36 C18 18 34 54 50 24 C64 12 76 60 94 30 C108 16 124 60 140 28 C156 12 170 62 188 28 C204 12 220 56 232 34"
      ];

      function pick(seed) {
        const color = colors[seed % colors.length];
        const path = paths[(seed >> 1) % paths.length];
        const width = 5 + (seed % 3); // 5,6,7
        const angle = -4 + (seed % 9); // -4..4
        const sizeX = 220 + ((seed >> 2) % 81); // 220..300
        return {
          pattern: makeScribbleDataUri(path, color, width),
          angle: `${angle}deg`,
          size: `${sizeX}px 100%`
        };
      }

      const leftSeed = hashText(`${seedText}_left`);
      const rightSeed = hashText(`${seedText}_right`);
      const left = pick(leftSeed);
      const right = pick(rightSeed + 11);
      return {
        leftPattern: left.pattern,
        rightPattern: right.pattern,
        leftAngle: left.angle,
        rightAngle: right.angle,
        leftSize: "100% 100%",
        rightSize: "100% 100%",
        sideWidth: "clamp(110px, 28%, 190px)"
      };
    }

    function randomizeFriendToys() {
      const surface = document.querySelector(".friend-surface");
      const ball = document.getElementById("friendToyBall");
      const bone = document.getElementById("friendToyBone");
      if (!surface || !ball || !bone) return;

      const width = surface.clientWidth;
      const safe = 14;
      const ballW = ball.offsetWidth || 42;
      const boneW = bone.offsetWidth || 78;
      if (width <= safe * 2 + ballW + boneW) return;

      const rand = (min, max) => Math.random() * (max - min) + min;
      const maxBallLeft = Math.max(safe, width - ballW - safe);
      const maxBoneLeft = Math.max(safe, width - boneW - safe);
      const minGap = ((ballW + boneW) / 2) + 22;

      let ballLeft = safe;
      let boneLeft = maxBoneLeft;
      for (let i = 0; i < 28; i += 1) {
        const nextBall = rand(safe, maxBallLeft);
        const nextBone = rand(safe, maxBoneLeft);
        const c1 = nextBall + ballW / 2;
        const c2 = nextBone + boneW / 2;
        if (Math.abs(c1 - c2) >= minGap) {
          ballLeft = nextBall;
          boneLeft = nextBone;
          break;
        }
        ballLeft = nextBall;
        boneLeft = nextBone;
      }

      ball.style.left = `${Math.round(ballLeft)}px`;
      ball.style.bottom = `${Math.round(rand(12, 34))}px`;

      bone.style.left = `${Math.round(boneLeft)}px`;
      bone.style.bottom = `${Math.round(rand(10, 30))}px`;
      bone.style.setProperty("--toy-rotate", `${Math.round(rand(-24, 14))}deg`);
    }

    function initFriendToyInteraction() {
      const ball = document.getElementById("friendToyBall");
      const bone = document.getElementById("friendToyBone");
      const bubble = document.getElementById("friendBubble");
      const friendToggle = document.getElementById("friendToggle");
      const friendNameplate = document.getElementById("friendNameplate");
      if (!ball || !bone || !bubble) return;
      if (ball.dataset.toyBound === "1" && bone.dataset.toyBound === "1") return;

      const toyMessagesByCharacter = {
        "참깨": [
          "꺄르르, 장난감 클릭 성공!\\n우리 재밌는 얘기하자 😜",
          "오호~ 반응 속도 최고인데?\\n나랑 바로 수다 모드 ON!",
          "장난 본능 발동했다!\\n오늘도 신나게 떠들어보자 🎉",
          "야호! 내가 기다렸지~\\n지금 바로 말 걸어줘 🐾",
          "짜잔~ 내가 먼저 놀아달라고 할까?\\n오늘 이야기 풀어줘!",
          "킥킥, 지금 분위기 완전 좋다!\\n우리 텐션 올려서 대화하자 ⚡",
          "폴짝! 장난감 신호 받았어!\\n재밌는 일부터 말해줘 🎈",
          "히히, 지금 수다 타이밍이다!\\n내가 리액션 크게 해줄게 😝"
        ],
        "들깨": [
          "토닥토닥, 눌러줘서 고마워.\\n지금 마음 천천히 들려줘 🤍",
          "오늘도 잘 버텼어.\\n편하게 이야기해도 괜찮아 🌷",
          "급하지 않아.\\n네 속도에 맞춰서 들어줄게.",
          "괜찮아, 내가 여기 있어.\\n조금씩 함께 정리해보자 🍀",
          "지금 이 순간도 충분히 잘하고 있어.\\n편하게 한마디만 해줘.",
          "마음이 복잡하면 한 줄부터 시작하자.\\n내가 차분히 들어줄게 🌿",
          "오늘 하루 어땠는지 궁금해.\\n작은 이야기부터 들려줘 🤍",
          "천천히 숨 쉬고,\\n내게 기대듯 이야기해도 돼."
        ],
        "통깨": [
          "우와! 장난감 클릭했다!\\n완전 반가워 😆",
          "헉헉 이 타이밍 뭐야!\\n당장 얘기하러 가자 💫",
          "리액션 풀충전 완료!\\n재밌는 얘기 시작해보자 🐶",
          "좋아좋아~ 느낌 왔어!\\n오늘 기분 마구 들려줘 💛",
          "와아 등장했다!\\n내가 공감 리액션 잔뜩 해줄게 ✨",
          "지금 딱 대화 버튼 눌러줘!\\n신나게 받아줄 준비 끝 😍",
          "오예~ 말 걸어주면\\n내가 먼저 맞장구 칠게 🎊",
          "오늘 무슨 일이 있었는지 궁금해!\\n같이 떠들자아 🫶"
        ],
        "흑깨": [
          "좋아, 시작 신호 확인했어.\\n차근차근 이야기해보자 📘",
          "잘했어. 지금부터\\n하나씩 정리해보면 돼.",
          "복잡해도 괜찮아.\\n순서대로 같이 풀어가자 🤝",
          "준비 완료.\\n필요한 것부터 천천히 말해줘.",
          "좋은 시작이야.\\n핵심부터 하나씩 점검해보자.",
          "어떤 주제든 괜찮아.\\n먼저 지금 상태부터 알려줘.",
          "잘하고 있어.\\n지금 생각나는 순서대로 말해줘도 돼.",
          "내가 옆에서 정리해줄게.\\n부담 없이 시작해보자."
        ]
      };
      const toyMessagesFallback = Object.values(toyMessagesByCharacter).flat();

      function getActiveCharacterForToy() {
        const byDataset = (friendToggle && friendToggle.dataset && friendToggle.dataset.characterId)
          ? String(friendToggle.dataset.characterId).trim()
          : "";
        if (byDataset) return byDataset;
        const byName = friendNameplate ? String(friendNameplate.textContent || "").trim() : "";
        return byName;
      }

      function getToyReactionMessages() {
        const characterId = getActiveCharacterForToy();
        return toyMessagesByCharacter[characterId] || toyMessagesFallback;
      }

      const onToyClick = (target) => {
        target.classList.remove("secret-pop");
        void target.offsetWidth;
        target.classList.add("secret-pop");
        window.setTimeout(() => target.classList.remove("secret-pop"), 320);
        const toyMessages = getToyReactionMessages();
        bubble.textContent = pickRandom(toyMessages) || toyMessages[0];
      };

      const bindToy = (el) => {
        const run = () => onToyClick(el);
        el.addEventListener("click", run);
        el.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            run();
          }
        });
        el.dataset.toyBound = "1";
      };

      bindToy(ball);
      bindToy(bone);
    }

    async function loadUiPreferences() {
      const pref = await apiJson("/api/v1/main/me/ui-preferences");
      stateCache.uiPreferences = pref || {
        top_toggle_highlight: null,
        nameplate_animation_enabled: false
      };
      return stateCache.uiPreferences;
    }

    async function patchUiPreferences(patch) {
      const pref = await apiJson("/api/v1/main/me/ui-preferences", {
        method: "PUT",
        body: JSON.stringify(patch)
      });
      stateCache.uiPreferences = pref;
      return pref;
    }

    function initTopToggleHighlights() {
      const toggles = Array.from(document.querySelectorAll(".bookmarkable[data-bookmark-key]"));
      const saved = (stateCache.uiPreferences && stateCache.uiPreferences.top_toggle_highlight) || null;

      if (saved) {
        const active = toggles.find((el) => el.dataset.bookmarkKey === saved);
        if (active) active.classList.add("bookmarked");
      }

      toggles.forEach((toggle) => {
        toggle.addEventListener("click", async () => {
          const key = toggle.dataset.bookmarkKey;
          if (!key) return;
          try {
            await patchUiPreferences({ top_toggle_highlight: key });
          } catch (_error) {}
          toggles.forEach((el) => el.classList.toggle("bookmarked", el === toggle));
        });
      });
    }

    function getTodayISO() {
      const now = new Date();
      const y = now.getFullYear();
      const m = String(now.getMonth() + 1).padStart(2, "0");
      const d = String(now.getDate()).padStart(2, "0");
      return `${y}-${m}-${d}`;
    }

    function msUntilNextMidnight() {
      const now = new Date();
      const next = new Date(now);
      next.setHours(24, 0, 0, 0);
      return Math.max(1000, next.getTime() - now.getTime());
    }

    function currentMedicationSlot(schedule) {
      const now = new Date();
      const nowMinutes = now.getHours() * 60 + now.getMinutes();
      const lunchParsed = parseTimeToMinutes(schedule.lunch);
      const eveningParsed = parseTimeToMinutes(schedule.evening);
      const lunch = lunchParsed === null ? parseTimeToMinutes(DEFAULT_MED_SCHEDULE.lunch) : lunchParsed;
      const evening = eveningParsed === null ? parseTimeToMinutes(DEFAULT_MED_SCHEDULE.evening) : eveningParsed;

      if (nowMinutes >= evening) {
        return { key: "evening", label: "저녁", baseTime: formatToAmPm(schedule.evening) };
      }
      if (nowMinutes >= lunch) {
        return { key: "lunch", label: "점심", baseTime: formatToAmPm(schedule.lunch) };
      }
      return { key: "morning", label: "아침", baseTime: formatToAmPm(schedule.morning) };
    }

    function toMidnight(dateObj) {
      const d = new Date(dateObj);
      d.setHours(0, 0, 0, 0);
      return d;
    }

    function formatDday(targetDateStr) {
      if (!targetDateStr) {
        return { meta: "다음 진료일까지", prefix: "D-", number: "00", urgencyClass: "" };
      }
      const today = toMidnight(new Date());
      const target = toMidnight(new Date(targetDateStr + "T00:00:00"));
      if (Number.isNaN(target.getTime())) {
        return { meta: "다음 진료일까지", prefix: "D-", number: "00", urgencyClass: "" };
      }
      const diffDays = Math.ceil((target - today) / 86400000);
      if (diffDays < 0) {
        return {
          meta: "진료일이 지났어요",
          prefix: "D+",
          number: String(Math.abs(diffDays)).padStart(2, "0"),
          urgencyClass: "overdue"
        };
      }
      let urgencyClass = "level-7plus";
      if (diffDays <= 0) urgencyClass = "level-0";
      else if (diffDays === 1) urgencyClass = "level-1";
      else if (diffDays === 2) urgencyClass = "level-2";
      else if (diffDays <= 4) urgencyClass = "level-3-4";
      else if (diffDays <= 6) urgencyClass = "level-5-6";
      return {
        meta: "다음 진료일까지",
        prefix: "D-",
        number: String(diffDays).padStart(2, "0"),
        urgencyClass
      };
    }

    async function fetchVisitSchedule() {
      const schedule = await apiJson("/api/v1/main/me/visit-schedule");
      stateCache.visitSchedule = schedule || { next_visit_date: null };
      return stateCache.visitSchedule;
    }

    async function saveVisitSchedule(nextVisitDate) {
      const saved = await apiJson("/api/v1/main/me/visit-schedule", {
        method: "PUT",
        body: JSON.stringify({ next_visit_date: nextVisitDate || null })
      });
      stateCache.visitSchedule = saved || { next_visit_date: nextVisitDate || null };
      return stateCache.visitSchedule;
    }

    async function initDdayToggle() {
      const toggle = document.getElementById("ddayToggle");
      const metaEl = document.getElementById("ddayMeta");
      const valueEl = document.getElementById("ddayValue");
      const modal = document.getElementById("ddayModal");
      const input = document.getElementById("ddayInput");
      const cancelBtn = document.getElementById("ddayCancelBtn");
      const saveBtn = document.getElementById("ddaySaveBtn");
      if (!toggle || !metaEl || !valueEl || !modal || !input || !cancelBtn || !saveBtn) return;

      const today = getTodayISO();
      input.min = today;

      function applyDisplay(dateStr) {
        const dday = formatDday(dateStr);
        metaEl.textContent = dday.meta;
        const numberClass = dday.urgencyClass ? `dday-number ${dday.urgencyClass}` : "dday-number";
        valueEl.innerHTML =
          `<span class="dday-prefix">${dday.prefix}</span>` +
          `<span class="${numberClass}">${dday.number}</span>`;
      }

      function openModal() {
        input.value = (stateCache.visitSchedule && stateCache.visitSchedule.next_visit_date) || "";
        modal.classList.add("show");
      }

      function closeModal() {
        modal.classList.remove("show");
      }

      toggle.onclick = openModal;
      cancelBtn.onclick = closeModal;
      saveBtn.onclick = async () => {
        const selected = input.value;
        if (!selected) {
          window.alert("진료일을 선택해주세요.");
          return;
        }
        stateCache.visitSchedule = { next_visit_date: selected };
        applyDisplay(selected);
        try {
          await saveVisitSchedule(selected);
        } catch (_error) {
          window.alert("저장 중 오류가 발생했어요. 잠시 후 다시 시도해주세요.");
        }
        closeModal();
      };

      modal.onclick = (event) => {
        if (event.target === modal) {
          closeModal();
        }
      };

      const savedDate = (stateCache.visitSchedule && stateCache.visitSchedule.next_visit_date) || "";
      applyDisplay(savedDate);
      try {
        const schedule = await fetchVisitSchedule();
        const fetchedDate = (schedule && schedule.next_visit_date) || "";
        applyDisplay(fetchedDate);
      } catch (_error) {
      }
    }

    async function renderMoodButtons() {
      const moodGrid = document.getElementById("moodGrid");
      if (!moodGrid) return;
      const today = getTodayISO();
      moodGrid.innerHTML = "";
      let remaining = DAILY_MOOD_STICKER_LIMIT;
      let recentMoodId = "";

      try {
        const stickers = await readDailyMoodStickers(today);
        if (Array.isArray(stickers) && stickers.length > 0) {
          let recent = stickers[stickers.length - 1];
          for (const item of stickers) {
            const itemTime = new Date(item && item.saved_at ? item.saved_at : 0).getTime();
            const recentTime = new Date(recent && recent.saved_at ? recent.saved_at : 0).getTime();
            if (itemTime >= recentTime) recent = item;
          }
          recentMoodId = String((recent && recent.mood_id) || "");
        }
      } catch (_error) {
      }

      try {
        remaining = await updateMoodRemainingInfo(today);
      } catch (_error) {
        const el = document.getElementById("moodRemaining");
        if (el) {
          el.innerHTML = `오늘 남은 스티커: <span class="remaining-count">${DAILY_MOOD_STICKER_LIMIT}</span>/${DAILY_MOOD_STICKER_LIMIT}`;
        }
      }
      const isLimitReached = remaining <= 0;
      moodLevels.forEach((mood) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "mood-btn";
        if (recentMoodId && mood.id === recentMoodId) {
          btn.classList.add("recent");
        }
        btn.disabled = isLimitReached;
        btn.style.setProperty("--mood-color", mood.color);
        btn.style.setProperty("--mood-face-color", mood.faceColor || "#fff8ef");
        btn.setAttribute("aria-label", mood.label);
        btn.innerHTML = `<span class=\"mood-color\" aria-hidden=\"true\"><span class=\"mood-face-art\" aria-hidden=\"true\">${getMoodFaceSvgMarkup(mood.id, mood.faceColor)}</span></span>`;
        btn.onclick = async () => {
          const currentRemaining = await updateMoodRemainingInfo(today);
          if (currentRemaining <= 0) {
            window.alert("오늘 기분 스티커는 하루 최대 4개까지 남길 수 있어요.");
            return;
          }

          const payload = {
            date: today,
            mood_id: mood.id,
            mood_label: mood.label,
            mood_sticker: mood.sticker,
            saved_at: new Date().toISOString()
          };
          let updated = [];
          try {
            updated = await createDailyMoodSticker(payload);
          } catch (error) {
            window.alert("스티커 저장 중 오류가 발생했어요.");
            return;
          }
          const params = buildDiaryParams(today, mood, updated);
          window.location.href = "/ui/diary?" + params.toString();
        };
        moodGrid.appendChild(btn);
      });
    }

    async function getMedicationIntakeCheckedSet(targetDateISO, slotKey) {
      const rows = await apiJson(
        `/api/v1/main/me/medication-intake?intake_date=${encodeURIComponent(targetDateISO)}&slot=${encodeURIComponent(slotKey)}`
      );
      const list = Array.isArray(rows) ? rows : [];
      const checked = new Set();
      list.forEach((row) => {
        if (row && row.checked && row.medication_plan_id) checked.add(String(row.medication_plan_id));
      });
      return checked;
    }

    async function getMedicationTakenCountMap() {
      const rows = await apiJson("/api/v1/main/me/medication-intake");
      const list = Array.isArray(rows) ? rows : [];
      const taken = new Map();
      list.forEach((row) => {
        if (!row || !row.checked || !row.medication_plan_id) return;
        const key = String(row.medication_plan_id);
        taken.set(key, (taken.get(key) || 0) + 1);
      });
      return taken;
    }

    function fallbackCheckStorageKey(dateISO, slotKey) {
      return `main_fallback_checks_v1_${dateISO}_${slotKey}`;
    }

    function readFallbackCheckedSet(dateISO, slotKey) {
      try {
        const raw = window.localStorage.getItem(fallbackCheckStorageKey(dateISO, slotKey));
        if (!raw) return new Set();
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) return new Set();
        return new Set(parsed.map((v) => String(v)));
      } catch (_error) {
        return new Set();
      }
    }

    function writeFallbackCheckedSet(dateISO, slotKey, checkedSet) {
      try {
        const arr = Array.from(checkedSet.values());
        window.localStorage.setItem(fallbackCheckStorageKey(dateISO, slotKey), JSON.stringify(arr));
      } catch (_error) {
      }
    }

    function renderMedicationFallbackList(medList, slotKey, dateISO) {
      const samples = [
        {
          name: "임시 복용약 A",
          dose: 1,
          times_per_day: 3,
          total_days: 7,
          image: "",
          effect: "기분과 수면 리듬 안정에 도움을 줄 수 있어요."
        },
        {
          name: "임시 복용약 B",
          dose: 0.5,
          times_per_day: 2,
          total_days: 10,
          image: "",
          effect: "긴장감 완화와 불안 조절에 도움을 줄 수 있어요."
        },
        {
          name: "임시 복용약 C",
          dose: 2,
          times_per_day: 1,
          total_days: 5,
          image: "",
          effect: "낮 시간 컨디션 유지에 도움을 줄 수 있어요."
        },
        {
          name: "임시 복용약 D",
          dose: 1.5,
          times_per_day: 3,
          total_days: 14,
          image: "",
          effect: "기분 기복 완화에 도움을 줄 수 있어요."
        },
        {
          name: "임시 복용약 E",
          dose: 0.25,
          times_per_day: 2,
          total_days: 7,
          image: "",
          effect: "야간 안정과 숙면 유도에 도움을 줄 수 있어요."
        },
      ];
      const checkedSet = readFallbackCheckedSet(dateISO, slotKey);
      medList.innerHTML = "";
      samples.forEach((med, index) => {
        const medDoseValue = Number(med.dose) || 1;
        const li = document.createElement("li");
        li.className = "med-item";
        const scribble = getRandomScribblePairStyle(`fallback_${index}`);
        li.style.setProperty("--scribble-left-pattern", scribble.leftPattern);
        li.style.setProperty("--scribble-right-pattern", scribble.rightPattern);
        li.style.setProperty("--scribble-left-angle", scribble.leftAngle);
        li.style.setProperty("--scribble-right-angle", scribble.rightAngle);
        li.style.setProperty("--scribble-left-size", scribble.leftSize);
        li.style.setProperty("--scribble-right-size", scribble.rightSize);
        li.style.setProperty("--scribble-side-width", scribble.sideWidth);
        const row = document.createElement("div");
        row.className = "med-row";
        const mainArea = document.createElement("div");
        mainArea.className = "med-main";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        const fallbackId = `fallback_${index}`;
        checkbox.id = fallbackId;
        checkbox.checked = checkedSet.has(fallbackId);

        const label = document.createElement("label");
        label.className = "med-label";
        label.htmlFor = checkbox.id;

        const medName = document.createElement("span");
        medName.className = "med-name";
        medName.textContent = med.name;

        const medDots = document.createElement("span");
        medDots.className = "med-dots";
        medDots.setAttribute("aria-hidden", "true");

        const medDose = document.createElement("span");
        medDose.className = "med-dose";
        medDose.textContent = formatDoseText(medDoseValue);

        const photoBtn = document.createElement("button");
        photoBtn.type = "button";
        photoBtn.className = "med-photo-btn";
        photoBtn.setAttribute("aria-label", `${med.name} 정보 보기`);

        const photo = document.createElement("img");
        photo.alt = `${med.name} 약 이미지`;
        photo.src = getMedicationDisplayImage(med.image);
        photo.loading = "lazy";
        photoBtn.appendChild(photo);

        const detail = document.createElement("div");
        detail.className = "med-detail";
        detail.classList.add(pickRandomPostitThemeClass());
        const remainLine = document.createElement("p");
        const remainDaysLine = document.createElement("p");
        const effectLine = document.createElement("p");

        const renderDetailText = () => {
          const totalNeed = medDoseValue * Number(med.times_per_day || 1) * Number(med.total_days || 1);
          const takenDose = checkbox.checked ? medDoseValue : 0;
          const remainDose = Math.max(0, totalNeed - takenDose);
          const remainDays = calculateRemainingMedicationDays(dateISO, med.total_days, dateISO);
          remainLine.textContent = `총 ${formatCountText(totalNeed)}정 중 ${formatCountText(remainDose)}정 남았어요.`;
          remainDaysLine.textContent = `남은 복용일 ${formatCountText(remainDays)}일`;
          effectLine.textContent = String(med.effect || "").trim() || "복용 안내 문구가 여기에 표시돼요.";
        };
        renderDetailText();
        detail.append(remainLine, remainDaysLine, effectLine);

        label.append(medName, medDots, medDose);
        mainArea.append(checkbox, label);
        row.append(mainArea, photoBtn);
        li.append(row, detail);

        photoBtn.onclick = () => {
          li.classList.toggle("open");
        };
        checkbox.onchange = () => {
          li.classList.toggle("checked", checkbox.checked);
          if (checkbox.checked) checkedSet.add(fallbackId);
          else checkedSet.delete(fallbackId);
          writeFallbackCheckedSet(dateISO, slotKey, checkedSet);
          renderDetailText();
        };
        li.classList.toggle("checked", checkbox.checked);
        medList.appendChild(li);
      });
    }

    async function renderMedicationList() {
      const schedule = await fetchMedicationSchedule();
      const slot = currentMedicationSlot(schedule);
      const medListTitle = document.getElementById("medListTitle");
      const medSlot = document.getElementById("medSlot");
      const medList = document.getElementById("medList");
      if (!medSlot || !medList) return;
      if (medListTitle) {
        medListTitle.textContent = `${slot.label} 복용약 리스트`;
      }
      medSlot.textContent = "적용 시간대 변경";

      let meds = [];
      let checked = new Set();
      let takenCountMap = new Map();
      const todayISO = getTodayISO();
      try {
        meds = await getMedicationsForSlot(slot.key, todayISO);
        const today = getTodayISO();
        [checked, takenCountMap] = await Promise.all([
          getMedicationIntakeCheckedSet(today, slot.key),
          getMedicationTakenCountMap()
        ]);
      } catch (_error) {
        renderMedicationFallbackList(medList, slot.key, todayISO);
        return;
      }
      medList.innerHTML = "";

      if (meds.length === 0) {
        renderMedicationFallbackList(medList, slot.key, todayISO);
        return;
      }

      meds.forEach((med, index) => {
        const medNameText = med.name || `복용약 ${index + 1}`;
        const medDoseValueRaw = Number(med.dose);
        const medDoseValue = Number.isFinite(medDoseValueRaw) && medDoseValueRaw > 0
          ? medDoseValueRaw
          : 1;
        const planId = String(med.id || index);
        const medId = `${slot.key}_${planId}`;
        const li = document.createElement("li");
        li.className = "med-item";
        const scribble = getRandomScribblePairStyle(medId);
        li.style.setProperty("--scribble-left-pattern", scribble.leftPattern);
        li.style.setProperty("--scribble-right-pattern", scribble.rightPattern);
        li.style.setProperty("--scribble-left-angle", scribble.leftAngle);
        li.style.setProperty("--scribble-right-angle", scribble.rightAngle);
        li.style.setProperty("--scribble-left-size", scribble.leftSize);
        li.style.setProperty("--scribble-right-size", scribble.rightSize);
        li.style.setProperty("--scribble-side-width", scribble.sideWidth);

        const row = document.createElement("div");
        row.className = "med-row";

        const mainArea = document.createElement("div");
        mainArea.className = "med-main";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.id = medId;
        checkbox.checked = checked.has(planId);

        const label = document.createElement("label");
        label.className = "med-label";
        label.htmlFor = medId;
        label.setAttribute("aria-label", `${medNameText} ${formatDoseText(medDoseValue)}`);

        const medName = document.createElement("span");
        medName.className = "med-name";
        medName.textContent = medNameText;

        const medDots = document.createElement("span");
        medDots.className = "med-dots";
        medDots.setAttribute("aria-hidden", "true");

        const medDose = document.createElement("span");
        medDose.className = "med-dose";
        medDose.textContent = formatDoseText(medDoseValue);

        label.append(medName, medDots, medDose);

        const photoBtn = document.createElement("button");
        photoBtn.type = "button";
        photoBtn.className = "med-photo-btn";
        photoBtn.setAttribute("aria-label", `${medNameText} 정보 보기`);

        const photo = document.createElement("img");
        photo.alt = `${medNameText} 약 이미지`;
        photo.src = getMedicationDisplayImage(med.medicine_image_url);
        photo.loading = "lazy";
        photoBtn.appendChild(photo);

        const detail = document.createElement("div");
        detail.className = "med-detail";
        detail.classList.add(pickRandomPostitThemeClass());
        const remainLine = document.createElement("p");
        const remainDaysLine = document.createElement("p");
        const effectLine = document.createElement("p");

        const effectText = String(med.medicine_effect_summary || "").trim() ||
          "복용 시간과 용량을 지키면 증상 완화에 도움을 줄 수 있어요.\\n궁금한 점은 진료 시 꼭 확인해 주세요.";

        const renderDetailText = () => {
          const takenCount = Number(takenCountMap.get(planId) || 0);
          const totalNeed = medDoseValue * Number(med.times_per_day || 1) * Number(med.total_days || 1);
          const takenDose = medDoseValue * takenCount;
          const remainDose = Math.max(0, totalNeed - takenDose);
          const remainDays = calculateRemainingMedicationDays(med.start_date, med.total_days, todayISO);
          remainLine.textContent =
            `총 ${formatCountText(totalNeed)}정 중 ${formatCountText(remainDose)}정 남았어요.`;
          remainDaysLine.textContent = `남은 복용일 ${formatCountText(remainDays)}일`;
          effectLine.textContent = effectText;
        };
        renderDetailText();
        detail.append(remainLine, remainDaysLine, effectLine);

        photoBtn.onclick = () => {
          li.classList.toggle("open");
        };

        const syncCheckedStyle = () => {
          li.classList.toggle("checked", checkbox.checked);
        };

        mainArea.append(checkbox, label);
        row.append(mainArea, photoBtn);
        li.append(row, detail);
        syncCheckedStyle();

        checkbox.onchange = async () => {
          const nextChecked = checkbox.checked;
          const wasChecked = checked.has(planId);
          try {
            await apiJson("/api/v1/main/me/medication-intake", {
              method: "PUT",
              body: JSON.stringify({
                medication_plan_id: med.id,
                intake_date: todayISO,
                slot: slot.key,
                checked: nextChecked
              })
            });
            if (nextChecked) checked.add(planId);
            else checked.delete(planId);
            if (!wasChecked && nextChecked) {
              takenCountMap.set(planId, Number(takenCountMap.get(planId) || 0) + 1);
            } else if (wasChecked && !nextChecked) {
              takenCountMap.set(planId, Math.max(0, Number(takenCountMap.get(planId) || 0) - 1));
            }
            renderDetailText();
          } catch (_error) {
            checkbox.checked = !nextChecked;
          }
          syncCheckedStyle();
        };

        medList.appendChild(li);
      });
    }

    function initMedicationScheduleEditor() {
      const modal = document.getElementById("medTimeModal");
      const openBtn = document.getElementById("medSlot");
      const cancelBtn = document.getElementById("medTimeCancelBtn");
      const saveBtn = document.getElementById("medTimeSaveBtn");
      const morningInput = document.getElementById("morningTimeInput");
      const lunchInput = document.getElementById("lunchTimeInput");
      const eveningInput = document.getElementById("eveningTimeInput");
      if (!modal || !openBtn || !cancelBtn || !saveBtn || !morningInput || !lunchInput || !eveningInput) return;

      async function openModal() {
        const schedule = await fetchMedicationSchedule();
        morningInput.value = schedule.morning;
        lunchInput.value = schedule.lunch;
        eveningInput.value = schedule.evening;
        modal.classList.add("show");
      }

      function closeModal() {
        modal.classList.remove("show");
      }

      openBtn.onclick = openModal;
      cancelBtn.onclick = closeModal;
      saveBtn.onclick = async () => {
        const nextSchedule = {
          morning: morningInput.value || DEFAULT_MED_SCHEDULE.morning,
          lunch: lunchInput.value || DEFAULT_MED_SCHEDULE.lunch,
          evening: eveningInput.value || DEFAULT_MED_SCHEDULE.evening
        };
        if (!isValidMedicationSchedule(nextSchedule)) {
          window.alert("시간 순서를 확인해주세요. (아침 < 점심 < 저녁)");
          return;
        }
        try {
          await saveMedicationSchedule(nextSchedule);
          await renderMedicationList();
        } catch (_error) {
          window.alert("시간 저장 중 오류가 발생했어요.");
          return;
        }
        closeModal();
      };

      modal.onclick = (event) => {
        if (event.target === modal) {
          closeModal();
        }
      };
    }

    function initMoodDailyResetWatcher() {
      function resetAtMidnight() {
        stateCache.moodByDate.clear();
        stateCache.moodRemainingByDate.clear();
        renderMoodButtons().catch(() => {});
        renderMedicationList().catch(() => {});
        window.setTimeout(resetAtMidnight, msUntilNextMidnight() + 500);
      }
      window.setTimeout(resetAtMidnight, msUntilNextMidnight() + 500);
    }

    function initNameplateAnimationToggle() {
      const plate = document.getElementById("friendNameplate");
      if (!plate) return;
      const initialEnabled = Boolean(
        stateCache.uiPreferences && stateCache.uiPreferences.nameplate_animation_enabled
      );

      function apply(enabled) {
        plate.classList.toggle("anim-off", !enabled);
        plate.setAttribute("aria-pressed", enabled ? "true" : "false");
        plate.setAttribute(
          "title",
          enabled ? "이름표 흔들림: 켜짐 (터치해서 끄기)" : "이름표 흔들림: 꺼짐 (터치해서 켜기)"
        );
      }

      async function toggle() {
        const nextEnabled = plate.classList.contains("anim-off");
        try {
          await patchUiPreferences({ nameplate_animation_enabled: nextEnabled });
        } catch (_error) {}
        apply(nextEnabled);
      }

      plate.addEventListener("click", () => {
        toggle().catch(() => {});
      });
      plate.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          toggle().catch(() => {});
        }
      });

      apply(initialEnabled);
    }

    async function loadFriendCard() {
      const friendImage = document.getElementById("friendImage");
      const friendBubble = document.getElementById("friendBubble");
      const friendToggle = document.getElementById("friendToggle");
      const friendNameplate = document.getElementById("friendNameplate");
      if (friendToggle && friendToggle.dataset) {
        friendToggle.dataset.characterId = "";
      }

      try {
        const myRes = await fetch("/api/v1/users/me/character", { headers: apiHeaders() });
        const my = await myRes.json();

        if (!my || !my.selected_character) {
          if (friendNameplate) friendNameplate.textContent = "내 친구";
          if (friendToggle && friendToggle.dataset) {
            friendToggle.dataset.characterId = "";
          }
          friendBubble.textContent = "먼저 친구를 선택해줘!\\n그러면 바로 대화할 수 있어.";
          setImageWithFallback(
            friendImage,
            ["/static/characters/chamkkae-removebg.png", "/static/characters/chamkkae.jpeg"],
            "친구를 먼저 선택해주세요"
          );
          friendToggle.onclick = () => {
            window.location.href = "/ui/friend/main?mode=first";
          };
          return;
        }

        const detailRes = await fetch(
          "/api/v1/users/characters/" + encodeURIComponent(my.selected_character),
          { headers: apiHeaders() }
        );
        const detail = await detailRes.json();
        const imageCandidates = buildChatbotImageCandidates(
          my.selected_character,
          (detail && detail.image_url) ? detail.image_url : null
        );
        if (friendNameplate) friendNameplate.textContent = my.selected_character;
        if (friendToggle && friendToggle.dataset) {
          friendToggle.dataset.characterId = my.selected_character;
        }
        setImageWithFallback(friendImage, imageCandidates, "내 친구 이미지");
        friendBubble.textContent = getChatBubbleText(my.selected_character);
        friendToggle.onclick = () => {
          window.location.href = "/ui/chatbot?friend=" + encodeURIComponent(my.selected_character);
        };
      } catch (error) {
        if (friendNameplate) friendNameplate.textContent = "내 친구";
        if (friendToggle && friendToggle.dataset) {
          friendToggle.dataset.characterId = "";
        }
        friendBubble.textContent = "친구를 다시 불러올게.\\n눌러서 선택 화면으로 갈래?";
        setImageWithFallback(
          friendImage,
          ["/static/characters/chamkkae-removebg.png", "/static/characters/chamkkae.jpeg"],
          "친구 이미지"
        );
        friendToggle.onclick = () => {
          window.location.href = "/ui/friend/main?mode=change";
        };
      }
    }

    async function safeStep(stepName, runner) {
      try {
        await runner();
      } catch (error) {
        console.error(`[init:${stepName}]`, error);
      }
    }

    async function initMainScreen() {
      const initialBubble = document.getElementById("friendBubble");
      if (initialBubble && !String(initialBubble.textContent || "").trim()) {
        initialBubble.textContent = "오늘은 어떤 이야기부터 해볼까?";
      }

      try {
        await loadUiPreferences();
      } catch (_error) {
        stateCache.uiPreferences = {
          top_toggle_highlight: null,
          nameplate_animation_enabled: false
        };
      }

      await safeStep("top_toggle", async () => { initTopToggleHighlights(); });
      await safeStep("nameplate_toggle", async () => { initNameplateAnimationToggle(); });
      await safeStep("med_schedule_editor", async () => { initMedicationScheduleEditor(); });
      await safeStep("toy_interaction", async () => { initFriendToyInteraction(); });

      // 친구 카드(이미지/말풍선)는 항상 먼저 시도해서
      // 다른 섹션 오류가 있어도 챗봇 토글이 사라지지 않도록 유지한다.
      await safeStep("friend_card", loadFriendCard);

      await safeStep("dday", initDdayToggle);
      await safeStep("mood", renderMoodButtons);
      await safeStep("medication_list", renderMedicationList);

      await safeStep("toy_randomize", async () => { randomizeFriendToys(); });
      initMoodDailyResetWatcher();
    }

    initMainScreen().catch((error) => {
      console.error("메인 초기화 실패:", error);
    });
  </script>
</body>
</html>
        """
    page = page.replace("__INITIAL_FRIEND_NAME__", html.escape(selected_name))
    page = page.replace("__INITIAL_FRIEND_IMAGE__", html.escape(selected_image))
    page = page.replace("__INITIAL_DDAY_META__", html.escape(initial_dday_meta))
    page = page.replace("__INITIAL_DDAY_PREFIX__", html.escape(initial_dday_prefix))
    page = page.replace("__INITIAL_DDAY_CLASS__", html.escape(initial_dday_class))
    page = page.replace("__INITIAL_DDAY_NUMBER__", html.escape(initial_dday_number))
    page = page.replace("__INITIAL_VISIT_DATE__", html.escape(initial_visit_date))
    return HTMLResponse(
        page,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


def _simple_page(title: str, description: str) -> HTMLResponse:
    safe_title = html.escape(title)
    safe_description = html.escape(description)
    return HTMLResponse(
        f"""
<!doctype html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <link rel="preload" href="/assets/fonts/MemomentKkukkukk.otf?v=20260301" as="font" type="font/otf" />
  <title>{safe_title}</title>
  <style>
    @font-face {{
      font-family: "MemomentKkukkukk";
      src: url("/assets/fonts/MemomentKkukkukk.otf?v=20260301") format("opentype"), local("MemomentKkukkukk");
      font-weight: 400;
      font-display: swap;
    }}
    * {{ box-sizing: border-box; }}
    html, body, button, input, select, textarea {{
      font-family: "MemomentKkukkukk", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    }}
    body {{
      margin: 0;
      min-height: 100dvh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      font-family: "MemomentKkukkukk", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
      background: linear-gradient(180deg, #f8f3ea, #f4efe2);
      color: #4a3a2a;
    }}
    .card {{
      width: 100%;
      max-width: 720px;
      border-radius: 20px;
      border: 1px solid rgba(188, 165, 140, 0.48);
      background: rgba(255, 252, 245, 0.96);
      box-shadow: 0 12px 24px rgba(110, 90, 70, 0.16);
      padding: 22px 18px;
    }}
    h1 {{ margin: 0; font-size: 1.42rem; color: #5a4432; }}
    p {{ margin: 10px 0 0; color: #7a6a58; line-height: 1.55; }}
    a {{
      margin-top: 14px;
      display: inline-block;
      text-decoration: none;
      color: #9b4f2d;
      border-bottom: 2px dashed rgba(195, 104, 70, 0.7);
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <section class="card">
    <h1>{safe_title}</h1>
    <p>{safe_description}</p>
    <a href="/ui/main">← 메인으로 돌아가기</a>
  </section>
</body>
</html>
        """
    )


@router.get("/ui/diary", response_class=HTMLResponse)
async def diary_ui(
    date: str | None = Query(default=None),
    mood: str | None = Query(default=None),
    label: str | None = Query(default=None),
    sticker: str | None = Query(default=None),
    mood_count: int | None = Query(default=None),
    labels: str | None = Query(default=None),
    stickers: str | None = Query(default=None),
) -> HTMLResponse:
    color_map = {
        "mood_1": "#e73a35",
        "mood_2": "#ec6a3b",
        "mood_3": "#f19a4a",
        "mood_4": "#f2c66a",
        "mood_5": "#90bde3",
        "mood_6": "#5b8fcc",
        "mood_7": "#2e67b1",
        "very_happy": "#e73a35",
        "happy": "#ec6a3b",
        "slightly_good": "#f19a4a",
        "neutral": "#f2c66a",
        "slightly_low": "#90bde3",
        "sad": "#5b8fcc",
        "very_sad": "#2e67b1",
    }

    sticker_ids: list[str] = []
    if sticker:
        sticker_ids.append(sticker.strip())
    if stickers:
        sticker_ids.extend([item.strip() for item in stickers.split(",") if item.strip()])
    if mood:
        sticker_ids.append(mood.strip())

    sticker_colors: list[str] = []
    seen: set[str] = set()
    for item in sticker_ids:
        if item in seen:
            continue
        seen.add(item)
        sticker_colors.append(color_map.get(item, "#c9c9c9"))

    if not sticker_colors:
        sticker_colors = ["#f2c66a"]

    safe_title = html.escape("다이어리")
    safe_date = html.escape(date) if date else "-"
    safe_label = html.escape(label) if label else "-"
    used_count = min(max(mood_count or 0, 0), 4)

    sticker_html = "".join(
        f'<span class="sticker-dot" style="background:{html.escape(color, quote=True)}"></span>'
        for color in sticker_colors[:4]
    )

    return HTMLResponse(
        f"""
<!doctype html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <link rel="preload" href="/assets/fonts/MemomentKkukkukk.otf?v=20260301" as="font" type="font/otf" />
  <title>{safe_title}</title>
  <style>
    @font-face {{
      font-family: "MemomentKkukkukk";
      src: url("/assets/fonts/MemomentKkukkukk.otf?v=20260301") format("opentype"), local("MemomentKkukkukk");
      font-weight: 400;
      font-display: swap;
    }}
    * {{ box-sizing: border-box; }}
    html, body, button, input, select, textarea {{
      font-family: "MemomentKkukkukk", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    }}
    body {{
      margin: 0;
      min-height: 100dvh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      background: linear-gradient(180deg, #f8f3ea, #f4efe2);
      color: #4a3a2a;
    }}
    .card {{
      width: 100%;
      max-width: 720px;
      border-radius: 20px;
      border: 1px solid rgba(188, 165, 140, 0.48);
      background: rgba(255, 252, 245, 0.96);
      box-shadow: 0 12px 24px rgba(110, 90, 70, 0.16);
      padding: 22px 18px;
    }}
    h1 {{ margin: 0; font-size: 1.42rem; color: #5a4432; }}
    .meta {{
      margin: 10px 0 0;
      font-size: 0.95rem;
      color: #7a6a58;
      line-height: 1.5;
    }}
    .sticker-wrap {{
      margin-top: 14px;
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .sticker-dot {{
      width: 34px;
      height: 34px;
      border-radius: 50%;
      border: 1px solid rgba(124, 100, 76, 0.26);
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.4),
        0 3px 6px rgba(96, 75, 55, 0.2);
    }}
    a {{
      margin-top: 14px;
      display: inline-block;
      text-decoration: none;
      color: #9b4f2d;
      border-bottom: 2px dashed rgba(195, 104, 70, 0.7);
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <section class="card">
    <h1>{safe_title}</h1>
    <p class="meta">날짜: {safe_date}</p>
    <p class="meta">기분: {safe_label}</p>
    <p class="meta">오늘 선택 횟수: {used_count}/4</p>
    <div class="sticker-wrap">{sticker_html}</div>
    <a href="/ui/main">← 메인으로 돌아가기</a>
  </section>
</body>
</html>
        """
    )


@router.get("/ui/dday", response_class=HTMLResponse)
async def dday_ui() -> HTMLResponse:
    return _simple_page(
        "진료 D-Day",
        "다음 진료일 등록/수정과 D-Day 확인 기능이 들어갈 페이지입니다.",
    )


@router.get("/ui/mypage", response_class=HTMLResponse)
async def mypage_ui() -> HTMLResponse:
    return _simple_page(
        "마이페이지",
        "프로필과 내 친구 변경, 계정 설정이 들어갈 페이지입니다.",
    )


@router.get("/ui/chatbot", response_class=HTMLResponse)
async def chatbot_ui(friend: str | None = Query(default=None)) -> HTMLResponse:
    friend_name = friend or "내 친구"
    return _simple_page(
        "챗봇",
        f"{friend_name}와 대화를 시작하는 페이지입니다.",
    )


@router.get("/ui/medications/add", response_class=HTMLResponse)
async def medication_add_ui() -> HTMLResponse:
    return _simple_page(
        "복용약 추가",
        "아침/점심/저녁 복용약을 등록하는 페이지입니다.",
    )


DAILY_MOOD_STICKER_LIMIT = 4


class MainProfileResponse(BaseModel):
    nickname: str | None = None
    profile_image_url: str | None = None


class MainProfileUpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=40)
    profile_image_url: str | None = Field(default=None, max_length=255)


class MainVisitScheduleResponse(BaseModel):
    next_visit_date: date | None = None


class MainVisitScheduleUpdateRequest(BaseModel):
    next_visit_date: date | None = None


class MainUiPreferenceResponse(BaseModel):
    top_toggle_highlight: str | None = None
    nameplate_animation_enabled: bool


class MainUiPreferenceUpdateRequest(BaseModel):
    top_toggle_highlight: str | None = Field(default=None, max_length=20)
    nameplate_animation_enabled: bool | None = None


class MainMedicationScheduleResponse(BaseModel):
    morning_time: str
    lunch_time: str
    evening_time: str


class MainMedicationScheduleUpdateRequest(BaseModel):
    morning_time: str | None = None
    lunch_time: str | None = None
    evening_time: str | None = None


class MainMedicationPlanCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    times_per_day: int = Field(ge=1, le=3)
    dose_per_take: float = Field(gt=0)
    total_days: int = Field(ge=1, le=365)
    start_date: date | None = None
    medicine_image_url: str | None = Field(default=None, max_length=500)
    medicine_effect_summary: str | None = Field(default=None, max_length=500)


class MainMedicationPlanResponse(BaseModel):
    id: str
    name: str
    times_per_day: int
    dose_per_take: float
    total_days: int
    start_date: date
    medicine_image_url: str | None = None
    medicine_effect_summary: str | None = None
    created_at: datetime


class MainMedicationIntakeUpdateRequest(BaseModel):
    medication_plan_id: str
    intake_date: date
    slot: Literal["morning", "lunch", "evening"]
    checked: bool = True


class MainMedicationIntakeResponse(BaseModel):
    medication_plan_id: str
    intake_date: date
    slot: Literal["morning", "lunch", "evening"]
    checked: bool
    checked_at: datetime


class MainMoodStickerCreateRequest(BaseModel):
    mood_date: date
    mood_id: str = Field(min_length=1, max_length=40)
    mood_label: str = Field(min_length=1, max_length=40)
    mood_sticker: str = Field(min_length=1, max_length=40)
    saved_at: datetime | None = None


class MainMoodStickerResponse(BaseModel):
    id: int
    mood_date: date
    mood_id: str
    mood_label: str
    mood_sticker: str
    saved_at: datetime


class MainMoodRemainingResponse(BaseModel):
    mood_date: date
    limit: int
    used: int
    remaining: int


async def get_main_user(x_user_id: Annotated[int | None, Header()] = None) -> FriendUser:
    return await ensure_friend_user(x_user_id or 1)


def _parse_hhmm_to_minutes(value: str) -> int | None:
    try:
        hh, mm = value.split(":")
        h = int(hh)
        m = int(mm)
    except Exception:
        return None
    if h < 0 or h > 23 or m < 0 or m > 59:
        return None
    return h * 60 + m


def _is_valid_schedule_order(morning: str, lunch: str, evening: str) -> bool:
    morning_minutes = _parse_hhmm_to_minutes(morning)
    lunch_minutes = _parse_hhmm_to_minutes(lunch)
    evening_minutes = _parse_hhmm_to_minutes(evening)
    if morning_minutes is None or lunch_minutes is None or evening_minutes is None:
        return False
    return morning_minutes < lunch_minutes < evening_minutes


@router.get("/api/v1/main/me/profile", response_model=MainProfileResponse)
async def get_main_profile(user: FriendUser = Depends(get_main_user)) -> MainProfileResponse:
    profile = await FriendUserProfile.get(user=user)
    return MainProfileResponse(
        nickname=profile.nickname,
        profile_image_url=profile.profile_image_url,
    )


@router.put("/api/v1/main/me/profile", response_model=MainProfileResponse)
async def update_main_profile(
    request: MainProfileUpdateRequest,
    user: FriendUser = Depends(get_main_user),
) -> MainProfileResponse:
    profile = await FriendUserProfile.get(user=user)
    changed_fields: list[str] = []
    if request.nickname is not None:
        profile.nickname = request.nickname.strip() or None
        changed_fields.append("nickname")
    if request.profile_image_url is not None:
        profile.profile_image_url = request.profile_image_url.strip() or None
        changed_fields.append("profile_image_url")
    if changed_fields:
        changed_fields.append("updated_at")
        await profile.save(update_fields=changed_fields)
    return MainProfileResponse(
        nickname=profile.nickname,
        profile_image_url=profile.profile_image_url,
    )


@router.get("/api/v1/main/me/visit-schedule", response_model=MainVisitScheduleResponse)
async def get_main_visit_schedule(
    user: FriendUser = Depends(get_main_user),
) -> MainVisitScheduleResponse:
    schedule = await FriendUserVisitSchedule.get(user=user)
    return MainVisitScheduleResponse(next_visit_date=schedule.next_visit_date)


@router.put("/api/v1/main/me/visit-schedule", response_model=MainVisitScheduleResponse)
async def update_main_visit_schedule(
    request: MainVisitScheduleUpdateRequest,
    user: FriendUser = Depends(get_main_user),
) -> MainVisitScheduleResponse:
    schedule = await FriendUserVisitSchedule.get(user=user)
    schedule.next_visit_date = request.next_visit_date
    await schedule.save(update_fields=["next_visit_date", "updated_at"])
    return MainVisitScheduleResponse(next_visit_date=schedule.next_visit_date)


@router.get("/api/v1/main/me/ui-preferences", response_model=MainUiPreferenceResponse)
async def get_main_ui_preferences(
    user: FriendUser = Depends(get_main_user),
) -> MainUiPreferenceResponse:
    pref = await FriendUserUiPreference.get(user=user)
    return MainUiPreferenceResponse(
        top_toggle_highlight=pref.top_toggle_highlight,
        nameplate_animation_enabled=pref.nameplate_animation_enabled,
    )


@router.put("/api/v1/main/me/ui-preferences", response_model=MainUiPreferenceResponse)
async def update_main_ui_preferences(
    request: MainUiPreferenceUpdateRequest,
    user: FriendUser = Depends(get_main_user),
) -> MainUiPreferenceResponse:
    pref = await FriendUserUiPreference.get(user=user)
    changed_fields: list[str] = []
    if request.top_toggle_highlight is not None:
        pref.top_toggle_highlight = request.top_toggle_highlight.strip() or None
        changed_fields.append("top_toggle_highlight")
    if request.nameplate_animation_enabled is not None:
        pref.nameplate_animation_enabled = request.nameplate_animation_enabled
        changed_fields.append("nameplate_animation_enabled")
    if changed_fields:
        changed_fields.append("updated_at")
        await pref.save(update_fields=changed_fields)
    return MainUiPreferenceResponse(
        top_toggle_highlight=pref.top_toggle_highlight,
        nameplate_animation_enabled=pref.nameplate_animation_enabled,
    )


@router.get("/api/v1/main/me/medication-schedule", response_model=MainMedicationScheduleResponse)
async def get_main_medication_schedule(
    user: FriendUser = Depends(get_main_user),
) -> MainMedicationScheduleResponse:
    schedule = await FriendUserMedicationSchedule.get(user=user)
    return MainMedicationScheduleResponse(
        morning_time=schedule.morning_time,
        lunch_time=schedule.lunch_time,
        evening_time=schedule.evening_time,
    )


@router.put("/api/v1/main/me/medication-schedule", response_model=MainMedicationScheduleResponse)
async def update_main_medication_schedule(
    request: MainMedicationScheduleUpdateRequest,
    user: FriendUser = Depends(get_main_user),
) -> MainMedicationScheduleResponse:
    schedule = await FriendUserMedicationSchedule.get(user=user)
    morning = request.morning_time or schedule.morning_time
    lunch = request.lunch_time or schedule.lunch_time
    evening = request.evening_time or schedule.evening_time
    if not _is_valid_schedule_order(morning, lunch, evening):
        raise HTTPException(status_code=422, detail="시간 순서를 확인해주세요. (아침 < 점심 < 저녁)")
    schedule.morning_time = morning
    schedule.lunch_time = lunch
    schedule.evening_time = evening
    await schedule.save(update_fields=["morning_time", "lunch_time", "evening_time", "updated_at"])
    return MainMedicationScheduleResponse(
        morning_time=schedule.morning_time,
        lunch_time=schedule.lunch_time,
        evening_time=schedule.evening_time,
    )


@router.get("/api/v1/main/me/medication-plans", response_model=list[MainMedicationPlanResponse])
async def get_main_medication_plans(
    target_date: date | None = Query(default=None),
    user: FriendUser = Depends(get_main_user),
) -> list[MainMedicationPlanResponse]:
    plans = await FriendMedicationPlan.filter(user=user).order_by("-created_at")
    if target_date is not None:
        plans = [plan for plan in plans if 0 <= (target_date - plan.start_date).days < plan.total_days]
    return [
        MainMedicationPlanResponse(
            id=plan.id,
            name=plan.name,
            times_per_day=plan.times_per_day,
            dose_per_take=plan.dose_per_take,
            total_days=plan.total_days,
            start_date=plan.start_date,
            medicine_image_url=plan.medicine_image_url,
            medicine_effect_summary=plan.medicine_effect_summary,
            created_at=plan.created_at,
        )
        for plan in plans
    ]


@router.post("/api/v1/main/me/medication-plans", response_model=MainMedicationPlanResponse)
async def create_main_medication_plan(
    request: MainMedicationPlanCreateRequest,
    user: FriendUser = Depends(get_main_user),
) -> MainMedicationPlanResponse:
    plan_id = f"med_{uuid4().hex[:16]}"
    start_date = request.start_date or date.today()
    plan = await FriendMedicationPlan.create(
        id=plan_id,
        user=user,
        name=request.name.strip(),
        times_per_day=request.times_per_day,
        dose_per_take=round(request.dose_per_take, 2),
        total_days=request.total_days,
        start_date=start_date,
        medicine_image_url=(request.medicine_image_url.strip() if request.medicine_image_url else None),
        medicine_effect_summary=(request.medicine_effect_summary.strip() if request.medicine_effect_summary else None),
    )
    return MainMedicationPlanResponse(
        id=plan.id,
        name=plan.name,
        times_per_day=plan.times_per_day,
        dose_per_take=plan.dose_per_take,
        total_days=plan.total_days,
        start_date=plan.start_date,
        medicine_image_url=plan.medicine_image_url,
        medicine_effect_summary=plan.medicine_effect_summary,
        created_at=plan.created_at,
    )


@router.delete("/api/v1/main/me/medication-plans/{plan_id}", status_code=204)
async def delete_main_medication_plan(
    plan_id: str,
    user: FriendUser = Depends(get_main_user),
) -> None:
    deleted = await FriendMedicationPlan.filter(id=plan_id, user=user).delete()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Medication plan not found")


@router.get("/api/v1/main/me/medication-intake", response_model=list[MainMedicationIntakeResponse])
async def get_main_medication_intake_logs(
    intake_date: date | None = Query(default=None),
    slot: Literal["morning", "lunch", "evening"] | None = Query(default=None),
    user: FriendUser = Depends(get_main_user),
) -> list[MainMedicationIntakeResponse]:
    query = FriendMedicationIntakeLog.filter(user=user)
    if intake_date is not None:
        query = query.filter(intake_date=intake_date)
    if slot is not None:
        query = query.filter(slot=slot)
    logs = await query.order_by("-checked_at")
    return [
        MainMedicationIntakeResponse(
            medication_plan_id=log.medication_plan_id,
            intake_date=log.intake_date,
            slot=log.slot,  # type: ignore[arg-type]
            checked=log.checked,
            checked_at=log.checked_at,
        )
        for log in logs
    ]


@router.put("/api/v1/main/me/medication-intake", response_model=MainMedicationIntakeResponse)
async def upsert_main_medication_intake_log(
    request: MainMedicationIntakeUpdateRequest,
    user: FriendUser = Depends(get_main_user),
) -> MainMedicationIntakeResponse:
    plan = await FriendMedicationPlan.get_or_none(id=request.medication_plan_id, user=user)
    if plan is None:
        raise HTTPException(status_code=404, detail="Medication plan not found")
    log, _ = await FriendMedicationIntakeLog.update_or_create(
        user=user,
        medication_plan=plan,
        intake_date=request.intake_date,
        slot=request.slot,
        defaults={
            "checked": request.checked,
            "checked_at": datetime.now(),
        },
    )
    return MainMedicationIntakeResponse(
        medication_plan_id=log.medication_plan_id,
        intake_date=log.intake_date,
        slot=log.slot,  # type: ignore[arg-type]
        checked=log.checked,
        checked_at=log.checked_at,
    )


@router.get("/api/v1/main/me/mood-stickers", response_model=list[MainMoodStickerResponse])
async def get_main_mood_stickers(
    mood_date: date | None = Query(default=None),
    user: FriendUser = Depends(get_main_user),
) -> list[MainMoodStickerResponse]:
    target_date = mood_date or date.today()
    rows = await FriendMoodSticker.filter(user=user, mood_date=target_date).order_by("saved_at")
    return [
        MainMoodStickerResponse(
            id=row.id,
            mood_date=row.mood_date,
            mood_id=row.mood_id,
            mood_label=row.mood_label,
            mood_sticker=row.mood_sticker,
            saved_at=row.saved_at,
        )
        for row in rows
    ]


@router.get("/api/v1/main/me/mood-stickers/remaining", response_model=MainMoodRemainingResponse)
async def get_main_mood_sticker_remaining(
    mood_date: date | None = Query(default=None),
    user: FriendUser = Depends(get_main_user),
) -> MainMoodRemainingResponse:
    target_date = mood_date or date.today()
    used = await FriendMoodSticker.filter(user=user, mood_date=target_date).count()
    remaining = max(0, DAILY_MOOD_STICKER_LIMIT - used)
    return MainMoodRemainingResponse(
        mood_date=target_date,
        limit=DAILY_MOOD_STICKER_LIMIT,
        used=used,
        remaining=remaining,
    )


@router.post("/api/v1/main/me/mood-stickers", response_model=MainMoodStickerResponse)
async def create_main_mood_sticker(
    request: MainMoodStickerCreateRequest,
    user: FriendUser = Depends(get_main_user),
) -> MainMoodStickerResponse:
    used = await FriendMoodSticker.filter(user=user, mood_date=request.mood_date).count()
    if used >= DAILY_MOOD_STICKER_LIMIT:
        raise HTTPException(status_code=409, detail="Daily mood sticker limit (4) exceeded")
    row = await FriendMoodSticker.create(
        user=user,
        mood_date=request.mood_date,
        mood_id=request.mood_id.strip(),
        mood_label=request.mood_label.strip(),
        mood_sticker=request.mood_sticker.strip(),
        saved_at=request.saved_at or datetime.now(),
    )
    return MainMoodStickerResponse(
        id=row.id,
        mood_date=row.mood_date,
        mood_id=row.mood_id,
        mood_label=row.mood_label,
        mood_sticker=row.mood_sticker,
        saved_at=row.saved_at,
    )
