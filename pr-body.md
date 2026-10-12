Adds **srezai** to *Skills & MCP* — a remote MCP server that supplies a generic web-access tool layer to a harness.

Why it belongs here rather than being "just another server": the tools are shaped around harness problems.
- **Context delivery:** pages come back as clean Markdown and can be read in token-sized windows (`read_url` with `maxChars`/`offset`, `read_urls` for batches), instead of dumping raw HTML into the context.
- **Tool design:** 12 narrowly-scoped tools (search, read, batch read, browser render, site map, crawl, schema extraction, claim verification, answer synthesis, deep research, free balance check) rather than one overloaded "do anything" tool.
- **Verification:** `verify_claim` reads independent sources and returns a verdict with quotes checked against page text — useful for the verification step of a harness.

Endpoint: `https://srezai.ru/api/mcp` (Streamable HTTP, `Authorization: Bearer <API key>`); keys and a free balance check at https://srezai.ru/dashboard. The linked repository is the MIT-licensed stdio bridge (`npx -y srezai-mcp`); the service itself is hosted. Strong Russian-web coverage is a practical advantage for anyone working outside English-language sources.

Русский: веб-поиск и чтение страниц в Markdown окнами, обход разделов сайта и проверка утверждений с цитатами — 12 инструментов для ИИ-агентов, сильное покрытие рунета.
