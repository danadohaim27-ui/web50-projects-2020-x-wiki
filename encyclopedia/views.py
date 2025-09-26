from django.shortcuts import render, redirect
from django.urls import reverse
from django import forms
from . import util
import random

# Try to use markdown2 if available; otherwise a lightweight fallback.
try:
    import markdown2
    def md_to_html(text: str) -> str:
        return markdown2.markdown(text or "")
except Exception:
    import re
    def md_to_html(text: str) -> str:
        """
        Minimal Markdown fallback supporting:
        #, ##, ### headings; **bold**; [text](url); unordered lists; paragraphs.
        Not full Markdown—good enough if markdown2 isn't installed.
        """
        if not text:
            return ""
        html = text

        # Escape basic HTML
        html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Headings
        html = re.sub(r"(?m)^###\s+(.*)$", r"<h3>\1</h3>", html)
        html = re.sub(r"(?m)^##\s+(.*)$", r"<h2>\1</h2>", html)
        html = re.sub(r"(?m)^#\s+(.*)$", r"<h1>\1</h1>", html)

        # Bold
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)

        # Links [text](url)
        html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

        # Unordered lists
        lines = html.splitlines()
        out, in_list = [], False
        import re as _re
        for line in lines:
            if _re.match(r"^\s*[-*]\s+", line):
                if not in_list:
                    out.append("<ul>")
                    in_list = True
                item = _re.sub(r"^\s*[-*]\s+", "", line)
                out.append(f"<li>{item}</li>")
            else:
                if in_list:
                    out.append("</ul>")
                    in_list = False
                out.append(line)
        if in_list:
            out.append("</ul>")
        html = "\n".join(out)

        # Paragraphs
        def wrap_para(block: str) -> str:
            if block.strip().startswith("<"):
                return block
            return f"<p>{block.strip()}</p>" if block.strip() else ""

        blocks = [wrap_para(b) for b in html.split("\n\n")]
        html = "\n\n".join(blocks)
        return html

class EntryForm(forms.Form):
    title = forms.CharField(
        label="Title",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Entry title"})
    )
    content = forms.CharField(
        label="Content (Markdown)",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 15, "placeholder": "# Heading\nSome **bold** text."})
    )

class EditForm(forms.Form):
    content = forms.CharField(
        label="Content (Markdown)",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 20})
    )

def index(request):
    return render(request, "encyclopedia/index.html", {
        "entries": util.list_entries()
    })

def entry(request, title):
    md = util.get_entry(title)
    if md is None:
        return render(request, "encyclopedia/error.html", {
            "message": f"The requested page '{title}' was not found."
        }, status=404)
    return render(request, "encyclopedia/entry.html", {
        "title": title,
        "content_html": md_to_html(md)
    })

def search(request):
    q = (request.GET.get("q") or "").strip()
    if not q:
        return redirect("encyclopedia:index")

    entries = util.list_entries()

    # Exact match (case-insensitive)
    for name in entries:
        if name.lower() == q.lower():
            return redirect("encyclopedia:entry", title=name)

    # Substring matches (case-insensitive)
    results = [name for name in entries if q.lower() in name.lower()]
    return render(request, "encyclopedia/search.html", {
        "query": q,
        "results": results
    })

def new_page(request):
    if request.method == "POST":
        form = EntryForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data["title"].strip()
            content = form.cleaned_data["content"]

            existing = util.list_entries()
            if any(e.lower() == title.lower() for e in existing):
                return render(request, "encyclopedia/new.html", {
                    "form": form,
                    "error": f"An entry named '{title}' already exists."
                }, status=400)

            util.save_entry(title, content)
            return redirect("encyclopedia:entry", title=title)
    else:
        form = EntryForm()

    return render(request, "encyclopedia/new.html", {"form": form})

def edit_page(request, title):
    md = util.get_entry(title)
    if md is None:
        return render(request, "encyclopedia/error.html", {
            "message": f"The requested page '{title}' was not found."
        }, status=404)

    if request.method == "POST":
        form = EditForm(request.POST)
        if form.is_valid():
            content = form.cleaned_data["content"]
            util.save_entry(title, content)
            return redirect("encyclopedia:entry", title=title)
    else:
        form = EditForm(initial={"content": md})

    return render(request, "encyclopedia/edit.html", {"title": title, "form": form})

def random_page(request):
    entries = util.list_entries()
    if not entries:
        return render(request, "encyclopedia/error.html", {
            "message": "No entries available."
        }, status=404)
    return redirect("encyclopedia:entry", title=random.choice(entries))
