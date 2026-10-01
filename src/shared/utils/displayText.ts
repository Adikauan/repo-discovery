export function formatDisplayIdentifier(value?: string, fallback = 'Unavailable reference') {
  if (!value) return fallback;
  let decoded: string;

  try {
    decoded = decodeURIComponent(value);
  } catch {
    return fallback;
  }

  decoded = decoded.replace(/[<>]/g, '').trim();
  if (!decoded || decoded.length > 120) return fallback;
  return decoded;
}
