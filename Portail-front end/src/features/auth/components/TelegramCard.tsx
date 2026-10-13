import { Check, MessageCircle, Unlink } from "lucide-react";
import { useState } from "react";

import { User, authApi } from "@/features/auth/api";
import { useAuth } from "@/features/auth/AuthContext";
import { Badge } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";
import { Card, CardContent } from "@/shared/components/ui/Card";
import { Input, Label } from "@/shared/components/ui/Field";

/**
 * Numéro professionnel de l'utilisateur connecté, qui ouvre l'accès au bot
 * Telegram. Le bot ne lie un compte Telegram que si le numéro partagé dans
 * Telegram est exactement celui-ci.
 */
export default function TelegramCard() {
  const { user, setUser } = useAuth();
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  if (!user) return null;

  const run = async (action: () => Promise<User>) => {
    setBusy(true);
    setError(null);
    try {
      const updated = await action();
      setUser(updated);
      setPhone(updated.phone ?? "");
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardContent className="space-y-4 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <MessageCircle className="h-4 w-4 text-primary" />
            <h2 className="font-semibold">Bot Telegram</h2>
          </div>
          {user.telegram_linked ? (
            <Badge tone="success">
              <Check className="mr-1 h-3 w-3" />
              Telegram lié
            </Badge>
          ) : (
            <Badge tone="neutral">Non lié</Badge>
          )}
        </div>
        <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Lancez et recevez vos rapports depuis Telegram. Inscrivez ici le numéro de votre
          compte Telegram, puis écrivez /start au bot et appuyez sur « Partager mon numéro ».
          Seul ce numéro donne accès aux données de l'agence ; le modifier délie Telegram.
        </p>

        {error && <p className="text-sm text-danger">{error}</p>}

        <div className="flex flex-wrap items-end gap-3">
          <div className="w-full max-w-xs">
            <Label htmlFor="telegram-phone">Mon numéro (Telegram)</Label>
            <Input
              id="telegram-phone"
              type="tel"
              autoComplete="tel"
              placeholder="+1 514 555-1234"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
          <Button
            variant="secondary"
            disabled={busy || phone.trim() === (user.phone ?? "")}
            onClick={() => run(() => authApi.updatePhone(phone.trim() || null))}
          >
            {saved ? "Enregistré" : "Enregistrer"}
          </Button>
          {user.telegram_linked && (
            <Button
              variant="ghost"
              size="sm"
              disabled={busy}
              onClick={() => run(() => authApi.unlinkTelegram())}
            >
              <Unlink className="h-3.5 w-3.5" />
              Délier Telegram
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
