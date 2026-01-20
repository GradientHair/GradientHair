export const getApiBase = () => {
  const envBase = process.env.NEXT_PUBLIC_API_URL;
  if (envBase && envBase.trim().length > 0) {
    return envBase;
  }

  if (typeof window === "undefined") {
    return "/api/v1";
  }

  const protocol = window.location.protocol === "https:" ? "https" : "http";
  const host = window.location.hostname || "localhost";
  return `${protocol}://${host}:8000/api/v1`;
};
