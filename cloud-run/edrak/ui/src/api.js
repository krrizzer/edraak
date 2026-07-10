const apiBase =
  import.meta.env.VITE_API_BASE_URL ||
  (window.location.port === "5173" ? "http://localhost:8080" : "");

export async function postJson(path, body, defaultError) {
  const response = await fetch(`${apiBase}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await responseError(response, defaultError));
  return response.json();
}

export async function getJson(path, defaultError) {
  const response = await fetch(`${apiBase}${path}`);
  if (!response.ok) throw new Error(await responseError(response, defaultError));
  return response.json();
}

async function responseError(response, defaultMessage) {
  try {
    const body = await response.json();
    if (body?.error) return body.error;
    if (body?.detail) return typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {
    // Keep the default message when the backend response is not JSON.
  }
  return defaultMessage;
}
