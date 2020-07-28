import mistune

class BootstrapAdmonitionRenderer(mistune.HTMLRenderer):
    def admonition(self,text,name,*args,**kwargs):
        if name in ['tip','hint','note']:
            mapped_name = 'info'
        elif name == 'important':
            mapped_name = 'primary'
        else:
            mapped_name = name
        return f"<div class='alert alert-{mapped_name}'>{text}</div>"
