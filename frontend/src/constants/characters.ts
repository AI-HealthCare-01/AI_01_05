import chamkkaeImg from "../assets/images/chatbots/chamkkae-removebg.png";
import deulkkaeImg from "../assets/images/chatbots/deulkkae-removebg.png";
import heukkkaeImg from "../assets/images/chatbots/heukkkae-removebg.png";
import tongkkaeImg from "../assets/images/chatbots/tongkkae-removebg.png";
import tongkkaeMood1Img from "../assets/images/chatbots/moods/tongkkae-mood-1.png";
import tongkkaeMood2Img from "../assets/images/chatbots/moods/tongkkae-mood-2.png";
import tongkkaeMood3Img from "../assets/images/chatbots/moods/tongkkae-mood-3.png";
import tongkkaeMood4Img from "../assets/images/chatbots/moods/tongkkae-mood-4.png";
import tongkkaeMood5Img from "../assets/images/chatbots/moods/tongkkae-mood-5.png";
import tongkkaeMood6Img from "../assets/images/chatbots/moods/tongkkae-mood-6.png";
import tongkkaeMood7Img from "../assets/images/chatbots/moods/tongkkae-mood-7.png";
import heukkkaeMood1Img from "../assets/images/chatbots/moods/heukkkae-mood-1.png";
import heukkkaeMood2Img from "../assets/images/chatbots/moods/heukkkae-mood-2.png";
import heukkkaeMood3Img from "../assets/images/chatbots/moods/heukkkae-mood-3.png";
import heukkkaeMood4Img from "../assets/images/chatbots/moods/heukkkae-mood-4.png";
import heukkkaeMood5Img from "../assets/images/chatbots/moods/heukkkae-mood-5.png";
import heukkkaeMood6Img from "../assets/images/chatbots/moods/heukkkae-mood-6.png";
import heukkkaeMood7Img from "../assets/images/chatbots/moods/heukkkae-mood-7.png";
import deulkkaeMood1Img from "../assets/images/chatbots/moods/deulkkae-mood-1.png";
import deulkkaeMood2Img from "../assets/images/chatbots/moods/deulkkae-mood-2.png";
import deulkkaeMood3Img from "../assets/images/chatbots/moods/deulkkae-mood-3.png";
import deulkkaeMood4Img from "../assets/images/chatbots/moods/deulkkae-mood-4.png";
import deulkkaeMood5Img from "../assets/images/chatbots/moods/deulkkae-mood-5.png";
import deulkkaeMood6Img from "../assets/images/chatbots/moods/deulkkae-mood-6.png";
import deulkkaeMood7Img from "../assets/images/chatbots/moods/deulkkae-mood-7.png";
import chamkkaeMood1Img from "../assets/images/chatbots/moods/chamkkae-mood-1.png";
import chamkkaeMood2Img from "../assets/images/chatbots/moods/chamkkae-mood-2.png";
import chamkkaeMood3Img from "../assets/images/chatbots/moods/chamkkae-mood-3.png";
import chamkkaeMood4Img from "../assets/images/chatbots/moods/chamkkae-mood-4.png";
import chamkkaeMood5Img from "../assets/images/chatbots/moods/chamkkae-mood-5.png";
import chamkkaeMood6Img from "../assets/images/chatbots/moods/chamkkae-mood-6.png";
import chamkkaeMood7Img from "../assets/images/chatbots/moods/chamkkae-mood-7.png";

export const CHARACTER_IMAGE_BY_ID: Record<number, string> = {
  1: chamkkaeImg,
  2: deulkkaeImg,
  3: heukkkaeImg,
  4: tongkkaeImg,
};

export const DEFAULT_CHARACTER_IMAGE = chamkkaeImg;

const CHARACTER_MOOD_IMAGE_BY_ID: Record<number, Partial<Record<number, string>>> = {
  1: {
    1: chamkkaeMood1Img,
    2: chamkkaeMood2Img,
    3: chamkkaeMood3Img,
    4: chamkkaeMood4Img,
    5: chamkkaeMood5Img,
    6: chamkkaeMood6Img,
    7: chamkkaeMood7Img,
  },
  2: {
    1: deulkkaeMood1Img,
    2: deulkkaeMood2Img,
    3: deulkkaeMood3Img,
    4: deulkkaeMood4Img,
    5: deulkkaeMood5Img,
    6: deulkkaeMood6Img,
    7: deulkkaeMood7Img,
  },
  3: {
    1: heukkkaeMood1Img,
    2: heukkkaeMood2Img,
    3: heukkkaeMood3Img,
    4: heukkkaeMood4Img,
    5: heukkkaeMood5Img,
    6: heukkkaeMood6Img,
    7: heukkkaeMood7Img,
  },
  4: {
    1: tongkkaeMood1Img,
    2: tongkkaeMood2Img,
    3: tongkkaeMood3Img,
    4: tongkkaeMood4Img,
    5: tongkkaeMood5Img,
    6: tongkkaeMood6Img,
    7: tongkkaeMood7Img,
  },
};

export function getCharacterImageByMood(characterId: number | null | undefined, moodLevel: number | null): string {
  if (!characterId) return DEFAULT_CHARACTER_IMAGE;
  if (!moodLevel) return CHARACTER_IMAGE_BY_ID[characterId] ?? DEFAULT_CHARACTER_IMAGE;
  return (
    CHARACTER_MOOD_IMAGE_BY_ID[characterId]?.[moodLevel] ??
    CHARACTER_IMAGE_BY_ID[characterId] ??
    DEFAULT_CHARACTER_IMAGE
  );
}
