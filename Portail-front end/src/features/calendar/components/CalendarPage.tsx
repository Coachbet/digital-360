import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  startOfMonth,
  startOfWeek,
  subMonths,
} from "date-fns";
import { fr } from "date-fns/locale";
import { ChevronLeft, ChevronRight, Plus, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { CalendarEvent, Category, calendarApi } from "@/features/calendar/api";
import { PageHeader } from "@/shared/components/AppLayout";
import { Badge } from "@/shared/components/ui/Badge";
import { Button } from "@/shared/components/ui/Button";
import { Card, CardContent } from "@/shared/components/ui/Card";
import { Input, Label, Select, Textarea } from "@/shared/components/ui/Field";
import { cn } from "@/shared/lib/utils";

const CATEGORY_COLOR: Record<string, string> = {
  report_deadline: "bg-primary",
  campaign: "bg-warning",
  client_meeting: "bg-success",
  internal: "bg-muted-foreground",
};

export default function CalendarPage() {
  const [cursor, setCursor] = useState(new Date());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedDay, setSelectedDay] = useState<Date>(new Date());
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const monthStart = startOfMonth(cursor);
  const monthEnd = endOfMonth(cursor);
  const gridStart = startOfWeek(monthStart, { weekStartsOn: 1 });
  const gridEnd = endOfWeek(monthEnd, { weekStartsOn: 1 });

  const days = useMemo(
    () => eachDayOfInterval({ start: gridStart, end: gridEnd }),
    [gridStart.getTime(), gridEnd.getTime()],
  );

  const refresh = () =>
    calendarApi
      .listEvents(gridStart, gridEnd)
      .then(setEvents)
      .catch((e) => setError(e.message));

  useEffect(() => {
    refresh();
  }, [cursor]);

  useEffect(() => {
    calendarApi.categories().then(setCategories).catch(() => undefined);
  }, []);

  const eventsOf = (day: Date) =>
    events.filter((e) => isSameDay(new Date(e.start_at), day));

  const dayEvents = eventsOf(selectedDay);

  return (
    <div>
      <PageHeader
        title="Calendrier"
        description="Échéances de rapports, campagnes, rendez-vous clients et planning interne."
        action={
          <Button onClick={() => setShowForm((v) => !v)}>
            <Plus className="h-4 w-4" />
            Nouvel événement
          </Button>
        }
      />

      {error && (
        <div className="mb-6 rounded-xl border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      {showForm && (
        <EventForm
          categories={categories}
          defaultDate={selectedDay}
          onCreated={() => {
            setShowForm(false);
            refresh();
          }}
          onError={setError}
        />
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <Card>
          <CardContent className="p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold capitalize">
                {format(cursor, "MMMM yyyy", { locale: fr })}
              </h2>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setCursor(subMonths(cursor, 1))}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setCursor(new Date())}>
                  Aujourd'hui
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setCursor(addMonths(cursor, 1))}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="mb-1 grid grid-cols-7 gap-1">
              {["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"].map((d) => (
                <div
                  key={d}
                  className="py-2 text-center text-xs font-medium text-muted-foreground"
                >
                  {d}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-1">
              {days.map((day) => {
                const dayItems = eventsOf(day);
                const isCurrentMonth = isSameMonth(day, cursor);
                const isSelected = isSameDay(day, selectedDay);
                const isToday = isSameDay(day, new Date());

                return (
                  <button
                    key={day.toISOString()}
                    onClick={() => setSelectedDay(day)}
                    className={cn(
                      "flex min-h-[72px] flex-col items-start gap-1 rounded-xl border p-2 text-left transition-colors",
                      isSelected
                        ? "border-primary bg-primary-soft"
                        : "border-transparent hover:bg-muted",
                      !isCurrentMonth && "opacity-40",
                    )}
                  >
                    <span
                      className={cn(
                        "text-xs font-medium",
                        isToday && "flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground",
                      )}
                    >
                      {format(day, "d")}
                    </span>
                    <div className="flex w-full flex-wrap gap-0.5">
                      {dayItems.slice(0, 3).map((e) => (
                        <span
                          key={e.id}
                          title={e.title}
                          className={cn(
                            "h-1.5 w-1.5 rounded-full",
                            CATEGORY_COLOR[e.category] ?? "bg-muted-foreground",
                          )}
                        />
                      ))}
                      {dayItems.length > 3 && (
                        <span className="text-[10px] text-muted-foreground">
                          +{dayItems.length - 3}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card className="h-fit">
          <CardContent className="p-5">
            <h3 className="mb-3 font-semibold capitalize">
              {format(selectedDay, "EEEE d MMMM", { locale: fr })}
            </h3>

            {dayEvents.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                Aucun événement
              </p>
            ) : (
              <ul className="space-y-3">
                {dayEvents.map((event) => (
                  <li key={event.id} className="rounded-xl border border-border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{event.title}</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {format(new Date(event.start_at), "HH:mm")} –{" "}
                          {format(new Date(event.end_at), "HH:mm")}
                        </p>
                        {event.description && (
                          <p className="mt-1.5 text-xs text-muted-foreground">
                            {event.description}
                          </p>
                        )}
                        <div className="mt-2 flex gap-1.5">
                          <Badge>
                            {categories.find((c) => c.value === event.category)?.label ??
                              event.category}
                          </Badge>
                          {event.source === "google" && <Badge tone="primary">Google</Badge>}
                        </div>
                      </div>
                      {event.source === "internal" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Supprimer"
                          onClick={() => calendarApi.remove(event.id).then(refresh)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function EventForm({
  categories,
  defaultDate,
  onCreated,
  onError,
}: {
  categories: Category[];
  defaultDate: Date;
  onCreated: () => void;
  onError: (m: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [date, setDate] = useState(format(defaultDate, "yyyy-MM-dd"));
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [category, setCategory] = useState("internal");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      await calendarApi.create({
        title,
        start_at: new Date(`${date}T${startTime}`).toISOString(),
        end_at: new Date(`${date}T${endTime}`).toISOString(),
        category,
        description: description || null,
      });
      setTitle("");
      setDescription("");
      onCreated();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="mb-6">
      <CardContent className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2">
          <Label htmlFor="ev-title">Titre</Label>
          <Input
            id="ev-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Rapport mensuel — Acme"
          />
        </div>
        <div>
          <Label htmlFor="ev-date">Date</Label>
          <Input id="ev-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="ev-cat">Catégorie</Label>
          <Select id="ev-cat" value={category} onChange={(e) => setCategory(e.target.value)}>
            {categories.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="ev-start">Début</Label>
          <Input
            id="ev-start"
            type="time"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="ev-end">Fin</Label>
          <Input
            id="ev-end"
            type="time"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
          />
        </div>
        <div className="sm:col-span-2">
          <Label htmlFor="ev-desc">Description</Label>
          <Textarea
            id="ev-desc"
            className="min-h-[40px]"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="flex items-end sm:col-span-2 lg:col-span-4">
          <Button disabled={!title || busy} onClick={submit}>
            {busy ? "Création..." : "Créer l'événement"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
