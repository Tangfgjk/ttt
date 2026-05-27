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
    .replace(/\\\\(?=[A-Za-z{}])/g, "\\");
}

function cleanQuestionContent(value: string) {
  const cleaned = styleDirectivePatterns
    .reduce((current, pattern) => current.replace(pattern, ""), value)
    .replace(/\sstyle\s*=\s*(["'])[\s\S]*?\1/gi, "");
  return normalizeLatexEscapes(cleaned);
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
  if (cleanedHtml.trim()) {
    return cleanedHtml;
  }

  const cleanedText = text ? cleanQuestionContent(text) : "";
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
