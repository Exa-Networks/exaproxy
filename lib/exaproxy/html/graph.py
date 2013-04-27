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
	google.setOnLoadCallback(drawChart_%(ident)d);
	function drawChart_%(ident)d() {
		var data = new google.visualization.DataTable();
%(columns)s
		data.addRows([
%(values)s
		]);

		var options = {
			width: 600, height: 500,
			title: '%(title)s',
			legend : {
				position: 'right',
				textStyle: {color: 'black', fontSize: 10}
			},
		};

		var chart = new google.visualization.LineChart(document.getElementById('chart_div_%(ident)d'));
		chart.draw(data, options);
	}
</script>
<div id="chart_div_%(ident)d"></div>
"""


def graph (monitor,title,reload_time,_keys,cumulative=False,split=False):
	data = []
	keys = [[_] for _ in _keys] if split else [_keys]

	for k in keys:
		columns = "data.addColumn('number', 'Seconds');\n" + '\n'.join(["data.addColumn('number', '%s');" % _ for _ in k])
		nb_records = len(monitor.history)
		last = [0]*len(k)

		chart = []
		index = monitor.nb_recorded - nb_records
		for values in monitor.history:
			if cumulative:
				new = [values[_] for _ in k]
				chart.append("[ %d, %s]" % (index, ','.join([str(max(0,n-l)).rstrip('L') for (n,l) in zip(new,last)])))
				last = new
			else:
				chart.append("[ %d, %s]" % (index, ','.join([str(values[_]) for _ in k])))
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
			'ident'  : len(data),
			'title'  : title,
			'columns': columns,
			'values' : values,
		})

	return (_chart_header % reload_time) + '\n'.join(data)
