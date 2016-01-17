{% extends "base.tpl" %}
{% block content %}	  
		<div class="span8">
		{% if not auth %}<a href="{{url}}">Вход в Flikr</a><br>{%endif%}
		{% for id, row in albums.iteritems() %}
			{{row.title}} фото {{row.photos}} ({{y_albums[row.yaf_id].imageCount}}) <a href="/sync/?id={{id}}">Синхронизировать</a> <a href="/clean/?id={{id}}">Очистить</a> </br>
		{% endfor %}
		</br>

		</div>
		<div class="span4">
		
		</div>
{% endblock %}