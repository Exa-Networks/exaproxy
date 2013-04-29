# encoding: utf-8
"""
graph.py

Created by Thomas Mangin on 2012-02-25.
Copyright (c) 2011-2013 Exa Networks. All rights reserved.
"""


_chart_header = """\
<script type="text/javascript" src="https://www.google.com/jsapi"></script>
<script language="javascript" type="text/javascript">
	setTimeout("location.reload();",%d);
	google.load("visualization", "1", {packages:["corechart"]});
</script>
"""

_chart = """\
<script type="text/javascript">
	google.setOnLoadCallback(drawChart_%(ident)s);
	function drawChart_%(ident)s() {
		var data = new google.visualization.DataTable();
%(columns)s
		data.addRows([
%(values)s
		]);

		var options = {
			width: 480, height: 500,
			title: '%(title)s',
			legend : {
				position: 'bottom',
				textStyle: {color: 'black', fontSize: 10}
			},
		};

		var chart = new google.visualization.LineChart(document.getElementById('chart_div_%(ident)s'));
		chart.draw(data, options);
	}
</script>
"""

def _nothing (value): return value

def graph (monitor,title,reload_time,_keys,cumulative=False,split=False,adaptor=_nothing):
	page = _chart_header % reload_time + '<div>'
	keys = [[_] for _ in _keys] if split else [_keys]

	for ident, interval,ratio in (('seconds','Seconds',1),('minutes','Minutes',60)):
		data = []
		datasource = getattr(monitor,ident)
		for k in keys:
			columns = "data.addColumn('number', '%s');\n" % interval + '\n'.join(["data.addColumn('number', '%s');" % _ for _ in k])
			nb_records = len(datasource)
			last = [0]*len(k)

			chart = []
			index = monitor.nb_recorded - nb_records
			for values in datasource:
				if cumulative:
					new = [values[_] for _ in k]
					chart.append("[ %d, %s]" % (index, ','.join([str(max(0,adaptor(n-l)/ratio)).rstrip('L') for (n,l) in zip(new,last)])))
					last = new
				else:
					chart.append("[ %d, %s]" % (index, ','.join([str(adaptor(values[_])) for _ in k])))
				index += 1

			if cumulative and chart:
				chart.pop(0)

			padding = []
			index = 0
			top = monitor.nb_recorded - nb_records
			while index < top:
				padding.append("[ %d, %s ]" % (index, ','.join(['0']*len(k))))
				index += 1
			values = ',\n'.join(padding + chart)

			data.append(_chart % {
				'ident'  : ident,
				'title'  : title + ' (%s)' % interval,
				'columns': columns,
				'values' : values,
			})
			page += '\n'.join(data) + '<div style="float: left;" id="chart_div_%s"></div>' % ident

	return page + '</div>'
