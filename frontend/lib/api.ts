export const getApiBase = () => {
  return process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";
};
