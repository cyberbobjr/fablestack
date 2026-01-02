"""
### extract_message_text
**Description :** Adapte un message ChatMessage (user, assistant, tool) pour en extraire le rôle et le texte à afficher à l'utilisateur. Pour les messages d'outil (role == 'tool'), extrait le résultat du tool (tool_call_results[0].result). Pour les autres rôles, retourne le texte du message.
**Paramètres :**
- `message` (ChatMessage) : Message à adapter.
**Retour :** Dictionnaire {"role": str, "content": str}.
"""
def extract_message_text(message):
    role = getattr(message, 'role', None)
    if hasattr(role, 'value'):
        role = role.value
    elif role is None and hasattr(message, '_role'):
        role = message._role.value
    else:
        role = str(role)
    if role == 'tool':
        if hasattr(message, 'tool_call_results') and message.tool_call_results:
            tool_result = message.tool_call_results[0]
            origin = getattr(tool_result, 'origin', None)
            content = getattr(tool_result, 'result', None)
            # Correction : sérialisation robuste du résultat
            if hasattr(content, 'to_dict'):
                content = content.to_dict()
            elif not isinstance(content, (str, int, float, bool, type(None), dict, list)):
                content = str(content)
            # Idem pour origin
            if hasattr(origin, 'to_dict'):
                origin = origin.to_dict()
            elif not isinstance(origin, (str, int, float, bool, type(None), dict, list)):
                origin = str(origin)
            return {"role": role, "content": content, "origin": origin}
        return {"role": role, "content": "", "origin": "unknown_tool"}
    else:
        text = getattr(message, 'text', None)
        if text:
            return {"role": role, "content": text}
        return {"role": role, "content": ""}
