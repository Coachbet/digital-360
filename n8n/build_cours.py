"""Génère les workflows n8n du projet de cours (version poste local).

Usage : python3 n8n/build_cours.py  → écrit dans n8n/cours/
Les workflows sont produits par script plutôt qu'à la main pour garder les
connexions cohérentes ; les JSON générés s'importent tels quels dans n8n.
"""

import json
import sys
import uuid
from pathlib import Path

# Cible : « local » (n8n dans Docker sur le Mac) ou « vps » (pile de production OVH).
# python3 n8n/build_cours.py        → n8n/cours/
# python3 n8n/build_cours.py vps    → n8n/cours/vps/
TARGET = sys.argv[1] if len(sys.argv) > 1 else "local"
OUT = Path(__file__).parent / "cours" / ("vps" if TARGET == "vps" else "")
BACKEND = "http://host.docker.internal:8001/api/v1"
OLLAMA_MODEL = "llama3.1"

# Sur le VPS, tous les services partagent le réseau Docker interne : on les
# joint par leur nom de service (voir deploy/docker-compose.prod.yml).
VPS_REPLACEMENTS = {
    "http://host.docker.internal:8001": "http://backend:8000",
    "http://host.docker.internal:11434": "http://ollama:11434",
    "http://host.docker.internal:9000": "http://minio:9000",
    "llama3.1": "llama3.2:3b",
}

TELEGRAM_CRED = {"telegramApi": {"id": "", "name": "adgi360 Bot"}}
BOT_API_CRED = {"httpHeaderAuth": {"id": "", "name": "adgi360 Bot API"}}
POSTGRES_CRED = {"postgres": {"id": "", "name": "adgi360 Postgres"}}
OLLAMA_CRED = {"ollamaApi": {"id": "", "name": "Ollama local"}}

RETRY = {"retryOnFail": True, "maxTries": 3, "waitBetweenTries": 3000}
# Identifiant Telegram du compte de test (le vôtre, lié dans le portail).
TEST_CHAT_ID = 0
CHAT = "={{ $('Extraire le message').first().json.chat_id }}"


class Flow:
    def __init__(self, name):
        self.name = name
        self.nodes = []
        self.connections = {}

    def node(self, name, type_, version, params, pos, **extra):
        n = {
            "parameters": params,
            "id": str(uuid.uuid4()),
            "name": name,
            "type": type_,
            "typeVersion": version,
            "position": list(pos),
        }
        n.update(extra)
        self.nodes.append(n)
        return name

    def link(self, src, dst, out=0, kind="main"):
        outs = self.connections.setdefault(src, {}).setdefault(kind, [])
        while len(outs) <= out:
            outs.append([])
        outs[out].append({"node": dst, "type": kind, "index": 0})

    def dump(self, filename, settings=None):
        names = {n["name"] for n in self.nodes}
        for src, kinds in self.connections.items():
            assert src in names, src
            for outs in kinds.values():
                for targets in outs:
                    for t in targets:
                        assert t["node"] in names, t["node"]
        data = {
            "name": self.name,
            "nodes": self.nodes,
            "connections": self.connections,
            "pinData": {},
            "active": False,
            "settings": {"executionOrder": "v1", **(settings or {})},
            "tags": [{"name": "adgi360"}],
        }
        text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if TARGET == "vps":
            for old, new in VPS_REPLACEMENTS.items():
                text = text.replace(old, new)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / filename).write_text(text)


# ---------------------------------------------------------------- helpers
def cond(left, op_type, operation, right="", single=False):
    op = {"type": op_type, "operation": operation}
    if single:
        op["singleValue"] = True
    return {"id": str(uuid.uuid4()), "leftValue": left, "rightValue": right, "operator": op}


def conditions(*items):
    return {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
        "conditions": list(items),
        "combinator": "and",
    }


def if_params(*items):
    return {"conditions": conditions(*items), "looseTypeValidation": True, "options": {}}


def switch_params(rules, fallback_name):
    return {
        "rules": {
            "values": [
                {"conditions": conditions(c), "renameOutput": True, "outputKey": key}
                for key, c in rules
            ]
        },
        "looseTypeValidation": True,
        "options": {"fallbackOutput": "extra", "renameFallbackOutput": fallback_name},
    }


def tg_text(chat, text, **extra):
    p = {
        "resource": "message",
        "operation": "sendMessage",
        "chatId": chat,
        "text": text,
        "additionalFields": {"appendAttribution": False},
    }
    p.update(extra)
    return p


def http(method, url, body=None, query=None, auth=True, timeout=30000, file=False):
    p = {"method": method, "url": url, "options": {"timeout": timeout}}
    if auth:
        p["authentication"] = "genericCredentialType"
        p["genericAuthType"] = "httpHeaderAuth"
    if body is not None:
        p.update({"sendBody": True, "specifyBody": "json", "jsonBody": body})
    if query:
        p["sendQuery"] = True
        p["queryParameters"] = {"parameters": [{"name": k, "value": v} for k, v in query]}
    if file:
        p["options"]["response"] = {"response": {"responseFormat": "file", "outputPropertyName": "data"}}
    return p


def assignments(*items, include_other=False):
    p = {
        "assignments": {
            "assignments": [
                {"id": str(uuid.uuid4()), "name": n, "value": v, "type": t} for n, v, t in items
            ]
        },
        "options": {},
    }
    if include_other:
        p["includeOtherFields"] = True
    return p


# ===================================================== 2. sous-workflow
def verifier_utilisateur():
    f = Flow("adgi360 – Vérifier l'utilisateur")
    f.node("Déclencheur", "n8n-nodes-base.executeWorkflowTrigger", 1.1,
           {"inputSource": "passthrough"}, (0, 0),
           notes="Appelé par le bot pour chaque message. Reçoit telegram_user_id, chat_type et text.")
    f.node("Chercher le compte", "n8n-nodes-base.postgres", 2.5, {
        "operation": "executeQuery",
        "query": (
            "SELECT u.id AS user_id, u.full_name, u.role, u.organization_id,\n"
            "       o.name AS organization_name\n"
            "FROM users u\n"
            "JOIN organizations o ON o.id = u.organization_id\n"
            "WHERE u.telegram_user_id = $1 AND u.is_active\n"
            "LIMIT 1;"
        ),
        "options": {"queryReplacement": "={{ [ $json.telegram_user_id ] }}"},
    }, (220, 0), credentials=POSTGRES_CRED, alwaysOutputData=True, **RETRY,
       notes="alwaysOutputData : sans ligne trouvée, le flux continue avec un objet vide au lieu de s'arrêter.")
    f.node("Construire le profil", "n8n-nodes-base.code", 2, {"jsCode": r"""// Décide si l'expéditeur a accès au bot.
// Deux conditions : compte Telegram lié à un utilisateur actif, et
// conversation privée (dans un groupe, d'autres personnes liraient la réponse).
const input = $('Déclencheur').first().json;
const row = $input.first().json || {};
const isPrivate = input.chat_type === 'private';
const known = Boolean(row.user_id) && isPrivate;

let outcome = 'accepted';
if (!isPrivate) outcome = 'group_refused';
else if (!row.user_id) outcome = 'unknown_user';

// Identifiant du journal généré ici : la colonne n'a pas de défaut en base.
const eventId = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
  const r = (Math.random() * 16) | 0;
  return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
});

return [{ json: {
  ...input,
  known,
  outcome,
  event_id: eventId,
  user: known ? {
    id: row.user_id,
    full_name: row.full_name,
    role: row.role,
    organization_id: row.organization_id,
    organization_name: row.organization_name,
  } : null,
} }];"""}, (440, 0))
    f.node("Journaliser l'accès", "n8n-nodes-base.postgres", 2.5, {
        "operation": "executeQuery",
        "query": (
            "INSERT INTO bot_events\n"
            "  (id, telegram_user_id, user_id, organization_id, outcome, message, update_id, created_at)\n"
            "VALUES ($1, $2, $3, $4, $5, $6, $7, now())\n"
            "ON CONFLICT (update_id) DO NOTHING\n"
            "RETURNING id;"
        ),
        "options": {"queryReplacement": (
            "={{ [ $json.event_id, $json.telegram_user_id, $json.user?.id ?? null, "
            "$json.user?.organization_id ?? null, $json.outcome, "
            "String($json.text || '').slice(0, 500), $json.update_id || null ] }}"
        )},
    }, (660, 0), credentials=POSTGRES_CRED, alwaysOutputData=True, **RETRY,
       notes="Trace d'accès (Loi 25) et idempotence : update_id est unique en base. "
             "Une mise à jour Telegram déjà vue n'insère rien et ne renvoie aucun id.")
    f.node("Retourner le profil", "n8n-nodes-base.set", 3.4, {
        "mode": "raw",
        "jsonOutput": "={{ { ...$('Construire le profil').first().json, duplicate: !$json.id } }}",
        "options": {},
    }, (880, 0), notes="Un sous-workflow renvoie la sortie de son dernier nœud : on renvoie le profil, "
             "avec duplicate = true si ce message avait déjà été traité.")
    f.link("Déclencheur", "Chercher le compte")
    f.link("Chercher le compte", "Construire le profil")
    f.link("Construire le profil", "Journaliser l'accès")
    f.link("Journaliser l'accès", "Retourner le profil")
    f.dump("2-adgi360-verifier-utilisateur.json")


# ===================================================== 3. bot Telegram
# Clavier permanent sous la zone de saisie : un clic par commande.
MENU_LABELS = {"📊 Rapport": "/rapport", "📁 Clients": "/clients", "⏳ Statut": "/statut", "❓ Aide": "/aide"}
MENU = dict(
    replyMarkup="replyKeyboard",
    replyKeyboard={"rows": [
        {"row": {"buttons": [{"text": "📊 Rapport"}, {"text": "📁 Clients"}]}},
        {"row": {"buttons": [{"text": "⏳ Statut"}, {"text": "❓ Aide"}]}},
    ]},
    replyKeyboardOptions={"resize_keyboard": True},
)

HELP = (
    "={{ 'Bonjour ' + ($json.user?.full_name || '') + ' 👋 (' + ($json.user?.organization_name || '') + ')\\n\\n' }}"
    "Utilisez les boutons sous la zone de saisie, ou :\n"
    "/rapport — choisir un client en un clic\n"
    "/rapport <client> [AAAA-MM] [-- consignes] — génère le rapport PowerPoint\n"
    "/statut — vos derniers rapports\n"
    "/clients — la liste de vos clients\n\n"
    "Vous pouvez aussi écrire normalement, par exemple :\n"
    "« fais-moi le rapport de Maison Boréale pour septembre »"
)

# Prompt système : rôle, intentions possibles, format de sortie imposé.
LLM_SYSTEM = """=Tu es l'assistant Telegram de Digital 360, une plateforme de rapports marketing pour agences.
Ta seule tâche : classer la demande de l'utilisateur. Tu ne réponds jamais directement à sa question.

Date du jour : {{ $now.toFormat('yyyy-MM-dd') }}

Intentions possibles :
- "rapport" : il veut générer un rapport de performance pour un client
- "statut" : il demande où en sont ses rapports
- "clients" : il veut la liste de ses clients
- "aide" : salutation, question hors sujet, ou demande incompréhensible

Réponds UNIQUEMENT avec un objet JSON de cette forme :
{"intent": "...", "client": "nom du client ou chaîne vide", "period": "AAAA-MM ou chaîne vide", "instructions": "consignes particulières ou chaîne vide"}

Pour « le mois dernier » ou un nom de mois, calcule la période à partir de la date du jour.
N'invente jamais de nom de client : recopie celui du message."""

# Message utilisateur : uniquement le texte reçu.
LLM_PROMPT = """=Message : \"\"\"{{ $json.text }}\"\"\""""


def bot_telegram():
    f = Flow("adgi360 – Bot Telegram")
    y = 0
    f.node("Message Telegram", "n8n-nodes-base.telegramTrigger", 1.1,
           {"updates": ["message", "callback_query"], "additionalFields": {}}, (0, y),
           credentials=TELEGRAM_CRED, webhookId=str(uuid.uuid4()),
           notes="Exige une URL HTTPS publique pour n8n (tunnel en local, domaine sur le VPS).")
    # Déclencheur à la demande : rejoue un vrai message Telegram sans téléphone.
    f.node("Test manuel", "n8n-nodes-base.manualTrigger", 1, {}, (0, y + 220),
           notes="Clic sur « Execute workflow » : rejoue l'exemple ci-dessous comme si le message venait de Telegram.")
    f.node("Exemple de message", "n8n-nodes-base.set", 3.4, {
        "mode": "raw",
        "jsonOutput": "={{ { update_id: Date.now(), message: { message_id: 1, "
                      "date: Math.floor(Date.now() / 1000), "
                      "chat: { id: TEST_CHAT_ID, type: 'private', first_name: 'Test' }, "
                      "from: { id: TEST_CHAT_ID, is_bot: false, first_name: 'Test' }, "
                      "text: '/clients' } } }}".replace("TEST_CHAT_ID", str(TEST_CHAT_ID)),
        "options": {},
    }, (0, y + 420), notes="Même forme qu'une mise à jour Telegram. update_id = Date.now() : "
                           "chaque essai est un nouveau message, l'idempotence ne le bloque pas.")
    f.node("Extraire le message", "n8n-nodes-base.set", 3.4, assignments(
        ("chat_id", "={{ ($json.message ?? $json.callback_query.message).chat.id }}", "number"),
        ("chat_type", "={{ ($json.message ?? $json.callback_query.message).chat.type }}", "string"),
        ("telegram_user_id", "={{ ($json.message ?? $json.callback_query).from.id }}", "number"),
        ("first_name", "={{ ($json.message ?? $json.callback_query).from.first_name || '' }}", "string"),
        ("text", "={{ $json.callback_query ? $json.callback_query.data : (" + json.dumps(MENU_LABELS, ensure_ascii=False)
         + "[($json.message.text || '').trim()] ?? ($json.message.text || '').trim()) }}", "string"),
        ("is_callback", "={{ Boolean($json.callback_query) }}", "boolean"),
        ("callback_id", "={{ $json.callback_query?.id || '' }}", "string"),
        ("has_contact", "={{ Boolean($json.message?.contact) }}", "boolean"),
        ("contact_phone", "={{ $json.message?.contact?.phone_number || '' }}", "string"),
        ("contact_user_id", "={{ $json.message?.contact?.user_id || 0 }}", "number"),
        ("update_id", "={{ $json.update_id || 0 }}", "number"),
    ), (220, y), notes="Un message, un clic sur un bouton ou un bouton du menu deviennent tous un « text » à interpréter.")
    f.node("Clic sur un bouton ?", "n8n-nodes-base.if", 2.2,
           if_params(cond("={{ $json.is_callback }}", "boolean", "true", single=True)), (440, y - 480))
    f.node("Accuser le clic", "n8n-nodes-base.telegram", 1.2, {
        "resource": "callback",
        "operation": "answerQuery",
        "queryId": "={{ $json.callback_id }}",
        "additionalFields": {},
    }, (660, y - 500), credentials=TELEGRAM_CRED, onError="continueRegularOutput", **RETRY,
       notes="Sans réponse au clic, Telegram laisse tourner un sablier sur le bouton.")
    f.node("Contact partagé ?", "n8n-nodes-base.if", 2.2,
           if_params(cond("={{ $json.has_contact }}", "boolean", "true", single=True)), (440, y))

    # --- branche liaison (contact partagé)
    f.node("Lier le compte", "n8n-nodes-base.httpRequest", 4.2, http(
        "POST", f"{BACKEND}/bot/link",
        body="={{ JSON.stringify({ telegram_user_id: $json.telegram_user_id, "
             "contact_user_id: $json.contact_user_id, phone: $json.contact_phone }) }}",
    ), (660, y - 260), credentials=BOT_API_CRED, onError="continueErrorOutput", **RETRY,
       notes="Le backend compare le numéro partagé à celui inscrit dans le portail et refuse un contact transféré.")
    f.node("Confirmer la liaison", "n8n-nodes-base.telegram", 1.2, tg_text(
        CHAT, "={{ $json.message }}", **MENU,
    ), (880, y - 300), credentials=TELEGRAM_CRED, **RETRY,
       notes="Remplace le bouton « Partager mon numéro » par le menu des commandes.")

    # --- branche message normal
    f.node("Vérifier l'utilisateur", "n8n-nodes-base.executeWorkflow", 1.2, {
        "workflowId": {"__rl": True, "value": "", "mode": "list",
                       "cachedResultName": "adgi360 – Vérifier l'utilisateur"},
        "options": {},
    }, (660, y + 40), notes="Sous-workflow : à sélectionner dans la liste après import.")
    f.node("Nouveau message ?", "n8n-nodes-base.if", 2.2,
           if_params(cond("={{ $json.duplicate !== true }}", "boolean", "true", single=True)), (660, y + 240),
           notes="Idempotence : un message déjà traité (même update_id) s'arrête ici, sans réponse ni rapport en double.")
    f.node("Utilisateur reconnu ?", "n8n-nodes-base.if", 2.2,
           if_params(cond("={{ $json.known }}", "boolean", "true", single=True)), (880, y + 40))
    f.node("Demander le numéro", "n8n-nodes-base.telegram", 1.2, tg_text(
        CHAT,
        "={{ $json.chat_type !== 'private' ? \"Je ne réponds qu'en conversation privée, pour protéger les données de votre agence.\" : "
        "'Bonjour ' + $json.first_name + \" 👋\\nPour accéder aux rapports de votre agence, je dois vérifier que votre numéro est inscrit dans Digital 360.\\nAppuyez sur le bouton ci-dessous.\" }}",
        replyMarkup="replyKeyboard",
        replyKeyboard={"rows": [{"row": {"buttons": [
            {"text": "📱 Partager mon numéro", "additionalFields": {"request_contact": True}}
        ]}}]},
        replyKeyboardOptions={"one_time_keyboard": True, "resize_keyboard": True},
    ), (1100, y + 240), credentials=TELEGRAM_CRED, **RETRY)

    f.node("Commande ou texte libre ?", "n8n-nodes-base.switch", 3.2, switch_params(
        [("commande", cond("={{ /^(\\/|[rp]\\|)/.test($json.text) }}", "boolean", "true", single=True))], "texte libre",
    ), (1100, y))
    f.node("Lire la commande", "n8n-nodes-base.code", 2, {"jsCode": r"""// /rapport Maison Boréale 2026-09 -- insister sur le ROAS
// ou un clic sur un bouton : « r|<client_id>|<période> » (lancer), « p|<client_id> » (choisir la période)
const ctx = $input.first().json;

if (/^[rp]\|/.test(ctx.text)) {
  const [kind, clientId, period] = ctx.text.split('|');
  return [{ json: {
    ...ctx,
    intent: kind === 'r' ? 'rapport' : 'periodes',
    client: '',
    client_id: clientId,
    period: period || null,
    instructions: null,
    source: 'bouton',
  } }];
}

const [head = '', ...rest] = ctx.text.split(/\s+/);
const command = head.toLowerCase().replace(/@.*$/, ''); // « /rapport@MonBot » dans un groupe

let args = rest.join(' ');
let instructions = null;
const sep = args.indexOf('--');
if (sep >= 0) {
  instructions = args.slice(sep + 2).trim() || null;
  args = args.slice(0, sep).trim();
}

let period = null;
const match = args.match(/\b(\d{4}-\d{2})\b/);
if (match) {
  period = match[1];
  args = args.replace(match[0], '').trim();
}

const intents = {
  '/rapport': 'rapport', '/report': 'rapport',
  '/statut': 'statut', '/status': 'statut',
  '/clients': 'clients',
  '/aide': 'aide', '/help': 'aide', '/start': 'aide',
};

return [{ json: {
  ...ctx,
  intent: intents[command] || 'aide',
  client: args,
  client_id: null,
  period,
  instructions,
  source: 'commande',
} }];"""}, (1320, y - 100))

    f.node("Comprendre la demande (IA)", "@n8n/n8n-nodes-langchain.chainLlm", 1.4, {
        "promptType": "define",
        "text": LLM_PROMPT,
        "messages": {"messageValues": [{"message": LLM_SYSTEM}]},
    }, (1320, y + 100), onError="continueErrorOutput", **RETRY,
       notes="Transforme une phrase libre en commande. Si Ollama est hors ligne, le bot propose les commandes au lieu de planter.")
    f.node("Ollama", "@n8n/n8n-nodes-langchain.lmChatOllama", 1, {
        "model": OLLAMA_MODEL,
        "options": {"temperature": 0, "format": "json"},
    }, (1320, y + 300), credentials=OLLAMA_CRED)
    f.node("Lire la réponse IA", "n8n-nodes-base.code", 2, {"jsCode": r"""// Le modèle répond en texte : on parse, et tout ce qui sort du cadre retombe sur « aide ».
const ctx = $("Vérifier l'utilisateur").first().json;
const raw = $input.first().json.text ?? '';

let answer = {};
try {
  answer = JSON.parse(raw);
} catch {
  const match = String(raw).match(/\{[\s\S]*\}/);
  try { answer = match ? JSON.parse(match[0]) : {}; } catch { answer = {}; }
}

const allowed = ['rapport', 'statut', 'clients', 'aide'];
return [{ json: {
  ...ctx,
  intent: allowed.includes(answer.intent) ? answer.intent : 'aide',
  client: String(answer.client || '').trim(),
  client_id: null,
  period: /^\d{4}-\d{2}$/.test(answer.period || '') ? answer.period : null,
  instructions: String(answer.instructions || '').trim() || null,
  source: 'ia',
} }];"""}, (1540, y + 100))
    f.node("IA indisponible", "n8n-nodes-base.telegram", 1.2, tg_text(
        CHAT,
        "Je n'arrive pas à interpréter votre message pour le moment (IA indisponible).\n"
        "Utilisez les commandes : /rapport <client>, /statut, /clients, /aide.",
    ), (1540, y + 300), credentials=TELEGRAM_CRED, **RETRY)

    f.node("Router l'intention", "n8n-nodes-base.switch", 3.2, switch_params([
        ("rapport", cond("={{ $json.intent }}", "string", "equals", "rapport")),
        ("statut", cond("={{ $json.intent }}", "string", "equals", "statut")),
        ("clients", cond("={{ $json.intent }}", "string", "equals", "clients")),
        ("periodes", cond("={{ $json.intent }}", "string", "equals", "periodes")),
    ], "aide"), (1760, y))

    # rapport
    f.node("Client précisé ?", "n8n-nodes-base.if", 2.2,
           if_params(cond("={{ $json.client || $json.client_id || '' }}", "string", "notEmpty", single=True)),
           (1980, y - 300), notes="Sans client précisé, on propose la liste en boutons au lieu d'un message d'usage.")
    f.node("Lancer le rapport", "n8n-nodes-base.httpRequest", 4.2, http(
        "POST", f"{BACKEND}/bot/reviews",
        body="={{ JSON.stringify({ telegram_user_id: $json.telegram_user_id, chat_id: $json.chat_id, "
             "client: $json.client, client_id: $json.client_id, period: $json.period, instructions: $json.instructions }) }}",
        timeout=60000,
    ), (2200, y - 360), credentials=BOT_API_CRED, onError="continueErrorOutput", **RETRY)
    f.node("Construire le clavier", "n8n-nodes-base.code", 2, {"jsCode": r"""// Transforme la liste des clients en boutons : un clic = un rapport.
// Un client avec une seule période lance directement le rapport ; avec
// plusieurs, un second clavier propose les périodes (les plus récentes d'abord).
// Le Switch a plusieurs sorties : on lit l'item sur celle qui a réellement servi.
let ctx;
for (let branch = 0; branch < 5 && !ctx; branch++) {
  try { ctx = $("Router l'intention").first(branch)?.json; } catch (e) { /* sortie non utilisée */ }
}
const res = $input.first().json;
if (!res.ok) {
  return [{ json: { chat_id: ctx.chat_id, text: res.message, keyboard: { rows: [] } } }];
}
const clients = res.clients || [];
let text;
let buttons;

if (ctx.intent === 'periodes') {
  const client = clients.find((c) => c.id === ctx.client_id);
  const periods = client?.periods || [];
  text = periods.length
    ? `📅 ${client.name} : quelle période ?`
    : `Aucun export .xlsx pour ${client?.name || 'ce client'}.`;
  buttons = periods.slice(0, 12).map((p) => ({
    text: p, additionalFields: { callback_data: `r|${client.id}|${p}` },
  }));
} else {
  const ready = clients.filter((c) => (c.periods || []).length);
  const waiting = clients.filter((c) => !(c.periods || []).length).map((c) => c.name);
  const intro = ctx.intent === 'clients' ? '📁 Vos clients. Touchez-en un pour lancer son rapport :' : '📊 Pour quel client ?';
  text = ready.length ? intro : "Aucun client n'a encore d'export .xlsx.";
  if (waiting.length) text += `\nSans données : ${waiting.join(', ')} (à déposer dans le portail, onglet Données).`;
  buttons = ready.slice(0, 20).map((c) => ({
    text: c.periods.length === 1 ? `${c.name} · ${c.periods[0]}` : `${c.name} ▸`,
    additionalFields: { callback_data: c.periods.length === 1 ? `r|${c.id}|${c.periods[0]}` : `p|${c.id}` },
  }));
}

// Deux boutons par ligne : lisible sur un téléphone.
const rows = [];
for (let i = 0; i < buttons.length; i += 2) rows.push({ row: { buttons: buttons.slice(i, i + 2) } });
// Format natif de l'API Telegram, envoyé tel quel par le nœud HTTP suivant.
const inline_keyboard = [];
for (let i = 0; i < buttons.length; i += 2) {
  inline_keyboard.push(buttons.slice(i, i + 2).map((b) => ({ text: b.text, callback_data: b.additionalFields.callback_data })));
}
return [{ json: { chat_id: ctx.chat_id, text, keyboard: { rows }, reply_markup: inline_keyboard.length ? { inline_keyboard } : undefined } }];"""}, (2420, y + 200))
    f.node("Proposer les choix", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST",
        "url": "=https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage",
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ chat_id: $json.chat_id, text: $json.text, reply_markup: $json.reply_markup }) }}",
        "options": {"timeout": 30000},
    }, (2640, y + 200), **RETRY,
       notes="Appel direct à l'API Telegram : le nœud Telegram n'accepte pas un clavier calculé (n8n 2.39). "
             "Le token vient de la variable d'environnement TELEGRAM_BOT_TOKEN : jamais écrit ici.")
    # statut / clients
    f.node("Derniers rapports", "n8n-nodes-base.httpRequest", 4.2, http(
        "GET", f"{BACKEND}/bot/reviews",
        query=[("telegram_user_id", "={{ $json.telegram_user_id }}"), ("limit", "5")],
    ), (2200, y), credentials=BOT_API_CRED, onError="continueErrorOutput", **RETRY)
    f.node("Liste des clients", "n8n-nodes-base.httpRequest", 4.2, http(
        "GET", f"{BACKEND}/bot/clients",
        query=[("telegram_user_id", "={{ $json.telegram_user_id }}")],
    ), (2200, y + 200), credentials=BOT_API_CRED, onError="continueErrorOutput", **RETRY)
    f.node("Répondre", "n8n-nodes-base.telegram", 1.2, tg_text(CHAT, "={{ $json.message }}"),
           (2420, y - 100), credentials=TELEGRAM_CRED, **RETRY,
           notes="Le backend renvoie toujours un message prêt à afficher, succès comme refus métier.")
    f.node("Aide", "n8n-nodes-base.telegram", 1.2, tg_text(CHAT, HELP, **MENU),
           (2200, y + 400), credentials=TELEGRAM_CRED, **RETRY)

    # erreurs techniques
    f.node("Portail indisponible", "n8n-nodes-base.telegram", 1.2, tg_text(
        CHAT, "⚠️ Le portail Digital 360 ne répond pas (3 tentatives). L'équipe technique est prévenue, réessayez dans quelques minutes.",
    ), (2420, y + 560), credentials=TELEGRAM_CRED, **RETRY)
    f.node("Signaler l'échec", "n8n-nodes-base.stopAndError", 1, {
        "errorMessage": "=Backend injoignable depuis le bot Telegram (utilisateur {{ $('Extraire le message').first().json.telegram_user_id }})",
    }, (2640, y + 560), notes="Fait échouer l'exécution pour déclencher le workflow d'alerte.")

    f.link("Message Telegram", "Extraire le message")
    f.link("Extraire le message", "Clic sur un bouton ?")
    f.link("Clic sur un bouton ?", "Accuser le clic", 0)
    f.link("Extraire le message", "Contact partagé ?")
    f.link("Contact partagé ?", "Lier le compte", 0)
    f.link("Contact partagé ?", "Vérifier l'utilisateur", 1)
    f.link("Lier le compte", "Confirmer la liaison", 0)
    f.link("Lier le compte", "Portail indisponible", 1)
    f.link("Vérifier l'utilisateur", "Nouveau message ?")
    f.link("Nouveau message ?", "Utilisateur reconnu ?", 0)
    f.link("Test manuel", "Exemple de message")
    f.link("Exemple de message", "Extraire le message")
    f.link("Utilisateur reconnu ?", "Commande ou texte libre ?", 0)
    f.link("Utilisateur reconnu ?", "Demander le numéro", 1)
    f.link("Commande ou texte libre ?", "Lire la commande", 0)
    f.link("Commande ou texte libre ?", "Comprendre la demande (IA)", 1)
    f.link("Ollama", "Comprendre la demande (IA)", 0, kind="ai_languageModel")
    f.link("Comprendre la demande (IA)", "Lire la réponse IA", 0)
    f.link("Comprendre la demande (IA)", "IA indisponible", 1)
    f.link("Lire la commande", "Router l'intention")
    f.link("Lire la réponse IA", "Router l'intention")
    f.link("Router l'intention", "Client précisé ?", 0)
    f.link("Router l'intention", "Derniers rapports", 1)
    f.link("Router l'intention", "Liste des clients", 2)
    f.link("Router l'intention", "Liste des clients", 3)
    f.link("Router l'intention", "Aide", 4)
    f.link("Client précisé ?", "Lancer le rapport", 0)
    f.link("Client précisé ?", "Liste des clients", 1)
    f.link("Liste des clients", "Construire le clavier", 0)
    f.link("Construire le clavier", "Proposer les choix")
    for n in ("Lancer le rapport", "Derniers rapports", "Liste des clients"):
        if n != "Liste des clients":
            f.link(n, "Répondre", 0)
        f.link(n, "Portail indisponible", 1)
    f.link("Portail indisponible", "Signaler l'échec")
    f.dump("3-adgi360-bot-telegram.json")


# Corps de l'appel Ollama du workflow auto-review, repris tel quel de la version locale.
OLLAMA_REPORT_BODY = "={{ JSON.stringify({\n  model: $json.ollama_model,\n  stream: false,\n  format: 'json',\n  options: { temperature: 0.4 },\n  prompt: `Tu es analyste chez ADIGI360, une agence de marketing digital. Rédige en français le plan d'un rapport de performance client, en t'appuyant uniquement sur les données fournies. N'invente aucun chiffre.\\n\\nClient : ${$json.client_name}\\nType de client : ${$json.client_type_label}\\nPériode : ${$json.period}\\nConsignes de l'équipe : ${$json.additional_info || 'aucune'}\\n\\nDonnées :\\n${JSON.stringify($json.resume)}\\n\\nRéponds UNIQUEMENT avec un objet JSON de cette forme exacte :\\n{\"title\": \"...\", \"subtitle\": \"...\", \"slides\": [\\n  {\"layout\": \"kpis\", \"title\": \"Chiffres clés\", \"kpis\": [{\"label\": \"...\", \"value\": \"...\", \"delta\": \"...\"}], \"bullets\": [\"...\"]},\\n  {\"layout\": \"bullets\", \"title\": \"Analyse\", \"subtitle\": \"...\", \"bullets\": [\"...\", \"...\"]},\\n  {\"layout\": \"recommendations\", \"title\": \"Recommandations\", \"items\": [{\"title\": \"...\", \"detail\": \"...\"}]}\\n]}\\n\\nRègles : 3 à 4 KPI maximum, 4 à 6 puces maximum par diapositive, 3 recommandations maximum. Les valeurs des KPI sont des chaînes déjà formatées (ex. \"18 400 $\", \"4,8x\"). Reste factuel et concis.`\n}) }}"


# ===================================================== 1. auto-review
def auto_review():
    f = Flow("adgi360 Auto Review")
    f.node("Webhook auto-review", "n8n-nodes-base.webhook", 2,
           {"httpMethod": "POST", "path": "auto-review", "options": {}}, (0, 0),
           webhookId="adgi360-auto-review",
           notes="Appelé par le backend quand une review est lancée, depuis le portail ou depuis le bot Telegram.")
    f.node("Préparer le contexte", "n8n-nodes-base.code", 2, {"jsCode": r"""// Contexte de la review + réglages du workflow.
// C'est le seul endroit à modifier pour changer de modèle IA.
const OLLAMA_URL = 'http://host.docker.internal:11434';
const OLLAMA_MODEL = '""" + OLLAMA_MODEL + r"""';  // doit être déjà téléchargé : ollama pull """ + OLLAMA_MODEL + r"""

const body = $input.first().json.body ?? $input.first().json;

if (!body.review_id) {
  throw new Error('Payload invalide : review_id manquant');
}
const files = body.source_files || [];
if (files.length === 0) {
  throw new Error('Aucun fichier source pour la review ' + body.review_id);
}

const context = {
  review_id: body.review_id,
  client_name: body.client?.name || 'Client',
  client_type_label: body.client_type_label || body.client_type || '',
  additional_info: body.additional_info || '',
  render_callback_url: body.render_callback_url,
  // Rappel d'échec : la review ne doit pas rester « en cours » si l'analyse plante.
  fail_callback_url: body.fail_callback_url
    || String(body.render_callback_url || '').replace('/render?', '/fail?'),
  // Renseigné quand la demande vient du bot : on renverra le PowerPoint dans Telegram.
  notify_chat_id: body.notify?.telegram_chat_id ?? null,
  period: [...new Set(files.map((f) => f.period))].join(', '),
  bucket: 'adgi360-files',
  ollama_url: OLLAMA_URL,
  ollama_model: OLLAMA_MODEL,
};

// Un item par fichier : les nœuds suivants les traitent en parallèle.
return files.map((file) => ({ json: { ...context, file } }));"""}, (220, 0))
    f.node("Télécharger le fichier source", "n8n-nodes-base.httpRequest", 4.2, {
        "url": "={{ $json.file.download_url || ('http://host.docker.internal:9000/' + $json.bucket + '/' + $json.file.storage_key) }}",
        "options": {"timeout": 60000, "response": {"response": {"responseFormat": "file", "outputPropertyName": "data"}}},
    }, (440, 0), onError="continueErrorOutput", **RETRY,
       notes="URL pré-signée émise par le backend (repli : bucket anonyme du poste de dev).")
    f.node("Extraire les données", "n8n-nodes-base.extractFromFile", 1,
           {"operation": "xlsx", "options": {}}, (660, 0))
    f.node("Résumer les données", "n8n-nodes-base.code", 2, {"jsCode": r"""// L'IA ne peut pas ingérer un export complet : on lui envoie une synthèse
// compacte — colonnes, nombre de lignes, totaux numériques et un échantillon.
const ctx = $('Préparer le contexte').first().json;
const rows = $input.all().map((item) => item.json).filter((r) => r && Object.keys(r).length);

if (rows.length === 0) {
  throw new Error('Aucune ligne extraite des fichiers sources');
}

const columns = [...new Set(rows.flatMap(Object.keys))].slice(0, 30);
const totals = {};
for (const col of columns) {
  const nums = rows
    .map((r) => Number(String(r[col]).replace(/[^0-9.,-]/g, '').replace(',', '.')))
    .filter((n) => Number.isFinite(n));
  if (nums.length >= rows.length * 0.6 && nums.length > 0) {
    totals[col] = {
      somme: Number(nums.reduce((a, b) => a + b, 0).toFixed(2)),
      moyenne: Number((nums.reduce((a, b) => a + b, 0) / nums.length).toFixed(2)),
      min: Math.min(...nums),
      max: Math.max(...nums),
    };
  }
}

const resume = {
  nombre_de_lignes: rows.length,
  colonnes: columns,
  totaux_numeriques: totals,
  echantillon: rows.slice(0, 15),
};

return [{ json: { ...ctx, resume } }];"""}, (880, 0))
    f.node("Analyse IA (Ollama)", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST",
        "url": "={{ $json.ollama_url }}/api/generate",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": OLLAMA_REPORT_BODY,
        "options": {"timeout": 300000},
    }, (1100, 0), onError="continueErrorOutput", retryOnFail=True, maxTries=2, waitBetweenTries=5000,
       notes="2 tentatives seulement : une génération peut prendre plusieurs minutes.")
    f.node("Valider le plan", "n8n-nodes-base.code", 2, {"jsCode": r"""// Ollama renvoie le JSON du modèle dans le champ « response » (chaîne).
// On le parse ici, avec un repli lisible si le modèle s'écarte du format :
// mieux vaut un rapport minimal qu'une exécution en échec.
const ctx = $('Résumer les données').first().json;
const raw = $input.first().json.response ?? '';

let plan;
try {
  plan = typeof raw === 'string' ? JSON.parse(raw) : raw;
} catch (e) {
  const match = String(raw).match(/\{[\s\S]*\}/);
  try { plan = match ? JSON.parse(match[0]) : null; } catch { plan = null; }
}

if (!plan || !Array.isArray(plan.slides) || plan.slides.length === 0) {
  plan = {
    title: `Rapport de performance — ${ctx.client_name}`,
    subtitle: ctx.period,
    slides: [{
      layout: 'bullets',
      title: 'Synthèse',
      bullets: [
        `${ctx.resume.nombre_de_lignes} lignes analysées sur la période ${ctx.period}.`,
        "L'analyse automatique n'a pas produit de plan exploitable — à compléter manuellement.",
      ],
    }],
  };
}

return [{ json: {
  review_id: ctx.review_id,
  render_callback_url: ctx.render_callback_url,
  notify_chat_id: ctx.notify_chat_id,
  plan,
} }];"""}, (1320, 0))
    f.node("Renvoyer le plan au portail", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST",
        "url": "={{ $json.render_callback_url }}",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify($json.plan) }}",
        "options": {"timeout": 180000},
    }, (1540, 0), onError="continueErrorOutput", **RETRY,
       notes="Le backend génère le PowerPoint aux couleurs de l'agence et bascule la review en « à relire ».")
    f.node("Demandé depuis Telegram ?", "n8n-nodes-base.if", 2.2, if_params(
        cond("={{ String($('Valider le plan').first().json.notify_chat_id ?? '') }}", "string", "notEmpty", single=True),
    ), (1760, 0))
    f.node("Terminé", "n8n-nodes-base.code", 2, {"jsCode": """return [{ json: {
  status: 'ok',
  review_id: $('Valider le plan').first().json.review_id,
  fichier: $('Renvoyer le plan au portail').first().json.report_filename,
  message: 'Rapport généré — en attente de relecture dans le portail',
} }];"""}, (1980, 120))
    f.node("Lien du PowerPoint", "n8n-nodes-base.httpRequest", 4.2, http(
        "GET", f"={BACKEND}/bot/reviews/{{{{ $('Valider le plan').first().json.review_id }}}}/download",
        query=[("telegram_user_id", "={{ $('Valider le plan').first().json.notify_chat_id }}")],
    ), (1980, -120), credentials=BOT_API_CRED, onError="continueErrorOutput", **RETRY)
    f.node("Récupérer le PowerPoint", "n8n-nodes-base.httpRequest", 4.2, http(
        "GET", "={{ $json.url }}", auth=False, timeout=60000, file=True,
    ), (2200, -120), onError="continueErrorOutput", **RETRY)
    f.node("Rédiger la légende", "n8n-nodes-base.code", 2, {"jsCode": r"""// Résumé de 5 lignes affiché sous le fichier dans Telegram (limite : 1024 caractères).
const plan = $('Valider le plan').first().json.plan;
const ctx = $('Préparer le contexte').first().json;
const kpiSlide = (plan.slides || []).find((s) => s.layout === 'kpis');
const kpis = (kpiSlide?.kpis || []).slice(0, 4)
  .map((k) => `• ${k.label} : ${k.value}${k.delta ? ` (${k.delta})` : ''}`);

const caption = [
  `📊 ${plan.title || 'Rapport de performance'}`,
  `${ctx.client_name}${ctx.period ? ' — ' + ctx.period : ''}`,
  ...kpis,
  '',
  '📝 À relire et valider dans le portail avant tout envoi au client.',
].join('\n').slice(0, 1000);

// On garde le fichier binaire : sans « binary », le PowerPoint serait perdu ici.
return [{ json: { caption, chat_id: ctx.notify_chat_id }, binary: $input.first().binary }];"""}, (2420, -120))
    f.node("Envoyer le PowerPoint", "n8n-nodes-base.telegram", 1.2, {
        "resource": "message",
        "operation": "sendDocument",
        "chatId": "={{ $json.chat_id }}",
        "binaryData": True,
        "binaryPropertyName": "data",
        "additionalFields": {"caption": "={{ $json.caption }}"},
    }, (2640, -120), credentials=TELEGRAM_CRED, **RETRY)

    # --- chemin d'échec
    f.node("Préparer l'échec", "n8n-nodes-base.code", 2, {"jsCode": r"""// Toutes les sorties d'erreur arrivent ici, après épuisement des tentatives.
const ctx = $('Préparer le contexte').first().json;
const err = $input.first().json.error;
const reason = (typeof err === 'string' ? err : err?.message) || 'Erreur inconnue';
return [{ json: {
  review_id: ctx.review_id,
  client_name: ctx.client_name,
  fail_callback_url: ctx.fail_callback_url,
  notify_chat_id: ctx.notify_chat_id,
  reason: String(reason).slice(0, 1500),
} }];"""}, (1320, 360))
    f.node("Marquer la review en échec", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST",
        "url": "={{ $json.fail_callback_url }}",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ reason: $json.reason }) }}",
        "options": {"timeout": 30000},
    }, (1540, 360), onError="continueRegularOutput", **RETRY,
       notes="Le portail affiche « Échec » au lieu de rester « en cours ».")
    f.node("Prévenir sur Telegram ?", "n8n-nodes-base.if", 2.2, if_params(
        cond("={{ String($('Préparer l\\'échec').first().json.notify_chat_id ?? '') }}", "string", "notEmpty", single=True),
    ), (1760, 360))
    f.node("Annoncer l'échec", "n8n-nodes-base.telegram", 1.2, tg_text(
        "={{ $('Préparer l\\'échec').first().json.notify_chat_id }}",
        "={{ '❌ Le rapport de ' + $('Préparer l\\'échec').first().json.client_name + \" n'a pas pu être généré.\\nCause : \" + $('Préparer l\\'échec').first().json.reason.slice(0, 300) + \"\\nL'équipe technique est prévenue.\" }}",
    ), (1980, 300), credentials=TELEGRAM_CRED, **RETRY)
    f.node("Analyse en échec", "n8n-nodes-base.stopAndError", 1, {
        "errorMessage": "={{ 'Review ' + $('Préparer l\\'échec').first().json.review_id + ' : ' + $('Préparer l\\'échec').first().json.reason }}",
    }, (2200, 380), notes="Marque l'exécution en échec pour déclencher le workflow d'alerte.")

    f.link("Webhook auto-review", "Préparer le contexte")
    f.link("Préparer le contexte", "Télécharger le fichier source")
    f.link("Télécharger le fichier source", "Extraire les données", 0)
    f.link("Télécharger le fichier source", "Préparer l'échec", 1)
    f.link("Extraire les données", "Résumer les données")
    f.link("Résumer les données", "Analyse IA (Ollama)")
    f.link("Analyse IA (Ollama)", "Valider le plan", 0)
    f.link("Analyse IA (Ollama)", "Préparer l'échec", 1)
    f.link("Valider le plan", "Renvoyer le plan au portail")
    f.link("Renvoyer le plan au portail", "Demandé depuis Telegram ?", 0)
    f.link("Renvoyer le plan au portail", "Préparer l'échec", 1)
    f.link("Demandé depuis Telegram ?", "Lien du PowerPoint", 0)
    f.link("Demandé depuis Telegram ?", "Terminé", 1)
    f.link("Lien du PowerPoint", "Récupérer le PowerPoint", 0)
    f.link("Lien du PowerPoint", "Terminé", 1)
    f.link("Récupérer le PowerPoint", "Rédiger la légende", 0)
    f.link("Récupérer le PowerPoint", "Terminé", 1)
    f.link("Rédiger la légende", "Envoyer le PowerPoint")
    f.link("Préparer l'échec", "Marquer la review en échec")
    f.link("Marquer la review en échec", "Prévenir sur Telegram ?")
    f.link("Prévenir sur Telegram ?", "Annoncer l'échec", 0)
    f.link("Prévenir sur Telegram ?", "Analyse en échec", 1)
    f.link("Annoncer l'échec", "Analyse en échec")
    f.dump("1-adgi360-auto-review.json", {"executionTimeout": 900})


# ===================================================== 4. alertes
def alertes():
    f = Flow("adgi360 – Alertes erreurs")
    f.node("Erreur dans un workflow", "n8n-nodes-base.errorTrigger", 1, {}, (0, 0),
           notes="Déclenché par n8n quand un workflow qui désigne celui-ci comme « Error workflow » échoue.")
    f.node("Configuration", "n8n-nodes-base.set", 3.4, assignments(
        ("admin_chat_id", "0", "number"), include_other=True,
    ), (220, 0), notes="Remplacer 0 par votre chat_id Telegram (visible dans une exécution du bot : chat.id).")
    f.node("Formater l'alerte", "n8n-nodes-base.code", 2, {"jsCode": r"""const e = $input.first().json;
const lines = [
  '🚨 Digital 360 — erreur n8n',
  `Workflow : ${e.workflow?.name || '?'}`,
  `Étape : ${e.execution?.lastNodeExecuted || '?'}`,
  `Erreur : ${String(e.execution?.error?.message || 'inconnue').slice(0, 500)}`,
  e.execution?.url ? `Exécution : ${e.execution.url}` : '',
];
return [{ json: { admin_chat_id: e.admin_chat_id, text: lines.filter(Boolean).join('\n') } }];"""}, (440, 0))
    f.node("Prévenir l'administrateur", "n8n-nodes-base.telegram", 1.2,
           tg_text("={{ $json.admin_chat_id }}", "={{ $json.text }}"), (660, 0),
           credentials=TELEGRAM_CRED, **RETRY)
    f.link("Erreur dans un workflow", "Configuration")
    f.link("Configuration", "Formater l'alerte")
    f.link("Formater l'alerte", "Prévenir l'administrateur")
    f.dump("4-adgi360-alertes-erreurs.json")


if __name__ == "__main__":
    verifier_utilisateur()
    bot_telegram()
    auto_review()
    alertes()
    print("Workflows écrits dans", OUT, file=sys.stderr)
