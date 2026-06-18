import renderMathInElement from "katex/contrib/auto-render";
import { useEffect, useRef } from "react";

type QuestionRichTextProps = {
  html?: string | null;
  text?: string | null;
  emptyLabel?: string;
  className?: string;
};

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function looksLikeHtml(value: string) {
  return /<\/?[a-z][\s\S]*>/i.test(value);
}

function decodeHtmlEntities(value: string) {
  return value
    .replace(/&nbsp;/gi, " ")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/&apos;/gi, "'");
}

function htmlToPlainText(value: string) {
  return decodeHtmlEntities(
    value
      .replace(/<\s*br\s*\/?>/gi, "\n")
      .replace(/<\/\s*(?:p|div|li|tr|section|article|h[1-6])\s*>/gi, "\n")
      .replace(/<[^>]+>/g, ""),
  );
}

function normalizeForCompleteness(value: string) {
  return value
    .replace(/\s+/g, "")
    .replace(/[，。；：、,.!?！？;:]/g, "")
    .trim();
}

function htmlLooksIncomplete(html: string, text: string) {
  const htmlPlain = normalizeForCompleteness(htmlToPlainText(html));
  const textPlain = normalizeForCompleteness(decodeHtmlEntities(text));

  if (textPlain.length < 16 || !htmlPlain) {
    return false;
  }

  if (htmlPlain.includes(textPlain)) {
    return false;
  }

  const htmlIsOnlyPartOfText = textPlain.includes(htmlPlain) && textPlain.length > htmlPlain.length + 12;
  const htmlMissesTextPrefix = !htmlPlain.includes(textPlain.slice(0, Math.min(18, textPlain.length)));
  const textIsMuchLonger = textPlain.length > htmlPlain.length * 1.28;

  return htmlIsOnlyPartOfText || (textIsMuchLonger && htmlMissesTextPrefix);
}

const knownFontFamilyPattern =
  "(?:Arial|Calibri|Cambria|Times New Roman|Times|Helvetica|Microsoft YaHei|SimSun|FangSong|KaiTi|宋体|黑体|楷体|仿宋|微软雅黑)";

const styleDirectivePatterns = [
  /\\style\s*\{\s*(?:font\s*-\s*family|font\s*-\s*size|font\s*-\s*weight|font\s*-\s*style|color|background\s*-\s*color|line\s*-\s*height)\s*:[^}]*\}/gi,
  new RegExp(
    String.raw`\\style\s*font\s*-\s*family\s*:\s*(?:"[^"]*"|'[^']*'|${knownFontFamilyPattern}(?:\s*,\s*${knownFontFamilyPattern})*)\s*;?`,
    "gi",
  ),
  /\\style\s*font\s*-\s*size\s*:\s*\d+(?:\.\d+)?\s*(?:px|pt|em|rem|%)\s*;?/gi,
  /\\style\s*(?:font\s*-\s*weight|font\s*-\s*style|color|background\s*-\s*color|line\s*-\s*height)\s*:\s*[^\\\s，。；;,）)]*\s*;?/gi,
];

function normalizeLatexEscapes(value: string) {
  return value
    .replace(/\\n(?=\s*[A-ZＡ-Ｚ0-9一-龥])/g, "\n")
    .replace(
      /\\\\(?=(?:frac|sqrt|left|right|times|cdot|le|ge|neq|begin|end|overline|underline|angle|parallel|perp|sin|cos|tan|log|ln|sum|int|alpha|beta|gamma|delta|pi|theta|lambda|mu|sigma|omega|infty|text|mathrm|mathbf)\b)/g,
      "\\",
    );
}

function normalizeLegacyMathMarkup(value: string) {
  return value
    .replace(/（\s*##\s*）/g, "(##)")
    .replace(/\(\s*##\s*\)/g, "(##)");
}

function cleanQuestionContent(value: string) {
  const cleaned = styleDirectivePatterns
    .reduce((current, pattern) => current.replace(pattern, ""), value)
    .replace(/\sstyle\s*=\s*(["'])[\s\S]*?\1/gi, "");
  return normalizeLegacyMathMarkup(normalizeLatexEscapes(cleaned));
}

function linkifyImageUrls(value: string) {
  const imageUrlPattern = /(https?:\/\/[^\s<>"']+\.(?:png|jpe?g|gif|webp|svg)(?:\?[^\s<>"']*)?)/gi;
  return value.replace(
    imageUrlPattern,
    (url) => `<img src="${url}" alt="题目图片" loading="lazy" />`,
  );
}

function buildMarkup(html?: string | null, text?: string | null) {
  const cleanedHtml = html ? cleanQuestionContent(html) : "";
  const cleanedText = text ? cleanQuestionContent(text) : "";

  if (cleanedHtml.trim() && (!cleanedText.trim() || !htmlLooksIncomplete(cleanedHtml, cleanedText))) {
    return cleanedHtml;
  }

  if (!cleanedText.trim()) {
    return "";
  }

  if (looksLikeHtml(cleanedText)) {
    return cleanedText;
  }

  return linkifyImageUrls(escapeHtml(cleanedText)).replace(/\n/g, "<br />");
}

export function QuestionRichText({
  html,
  text,
  emptyLabel = "暂无内容",
  className,
}: QuestionRichTextProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const markup = buildMarkup(html, text);

  useEffect(() => {
    if (!containerRef.current || !markup) {
      return;
    }

    renderMathInElement(containerRef.current, {
      throwOnError: false,
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "(##)", right: "(##)", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false },
      ],
    });
  }, [markup]);

  if (!markup) {
    return <span className="question-rich-text__empty">{emptyLabel}</span>;
  }

  return (
    <div
      className={className ? `question-rich-text ${className}` : "question-rich-text"}
      ref={containerRef}
      dangerouslySetInnerHTML={{ __html: markup }}
    />
  );
}
