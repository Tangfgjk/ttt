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

function linkifyImageUrls(value: string) {
  const imageUrlPattern = /(https?:\/\/[^\s<>"']+\.(?:png|jpe?g|gif|webp|svg)(?:\?[^\s<>"']*)?)/gi;
  return value.replace(
    imageUrlPattern,
    (url) => `<img src="${url}" alt="题目图片" loading="lazy" />`,
  );
}

function buildMarkup(html?: string | null, text?: string | null) {
  if (html?.trim()) {
    return html;
  }

  if (!text?.trim()) {
    return "";
  }

  if (looksLikeHtml(text)) {
    return text;
  }

  return linkifyImageUrls(escapeHtml(text)).replace(/\n/g, "<br />");
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
