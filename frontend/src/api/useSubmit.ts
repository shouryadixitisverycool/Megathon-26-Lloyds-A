import { useSave } from "./hooks";
import { useToast } from "../components/Toast";

/** Writes through the API, then confirms with the audit event ID the server recorded. */
export function useSubmit<T = Record<string, unknown>>(path: string, invalidate: unknown[][], success: string) {
  const save = useSave<T>(path, invalidate);
  const toast = useToast();
  const submit = (payload: Record<string, unknown>) =>
    save.mutate(payload, {
      onSuccess: (result) => {
        const record = result as Record<string, unknown>;
        toast({
          kind: "success",
          title: success,
          detail: typeof record?.limitation === "string" ? record.limitation : undefined,
          auditId: typeof record?.id === "string" ? record.id : typeof record?.campaign_event_id === "string" ? record.campaign_event_id : undefined,
        });
      },
      onError: (error) => toast({ kind: "error", title: "Not saved", detail: (error as Error).message }),
    });
  return { ...save, submit };
}
