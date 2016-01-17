<!DOCTYPE html>
{% autoescape true %}
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Flickr - Yandex Tunnel - FYTunnel{% endblock %}</title>
    <link href="/css/bootstrap.css" rel="stylesheet">
    <link href="/css/bootstrap-responsive.css" rel="stylesheet">
    <link href="/css/tablecloth.css" rel="stylesheet">
    <link href="/css/prettify.css" rel="stylesheet"> 
	<script src="/js/jquery-1.7.2.min.js"></script>
    <script src="/js/bootstrap.js"></script>
    <script src="/js/jquery.metadata.js"></script>
    <script src="/js/jquery.tablesorter.min.js"></script>
    <script src="/js/jquery.tablecloth.js"></script>
	{% block head%}{% endblock %}
  </head> 
  <body>

    <div class="container">
      <div class="row">
		{% block menu %}
		<div class="span12" style="padding-top:20px;"> 
		<ul class="nav nav-tabs">
			{% for item in menu %}
			<li {% if active==item.id %}class="active"{%endif%}><a href="{{item.url}}">{{item.name}}</a></li>
			{% endfor %}
		</ul>
		</div>
		{% endblock %}
		{% block content %}{% endblock %}
		{{ raw_content|safe }}
     </div>
	</div>
    
    <script type="text/javascript" charset="utf-8">
      $(document).ready(function() {
	  $('#actualization').on('click', function (e) {
			if (!$(this).hasClass("active")) {$(".nonactual").hide();} else {$(".nonactual").show();}
		});
		$('#ingarage').on('click', function (e) {
			if (!$(this).hasClass("active")) {$(".noingarage").hide();} else {$(".noingarage").show();}
		});
	  if ($("[rel=tooltip]").length) {
		$("[rel=tooltip]").tooltip();
		}
		$("#tanks").tablecloth({
          theme: "stats",
          striped: true,
          sortable: true,
          condensed: true
        });
	  $("#stats").tablecloth({
          theme: "default",
          striped: true,
          sortable: false,
          condensed: true
        });
        $("#result").tablecloth({
          theme: "paper",
          striped: true,
          sortable: true,
          condensed: true
        });
		
      });
    </script> 
  </body>
</html>
{% endautoescape %}