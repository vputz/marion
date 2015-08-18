// must have included several things; should move to "require" at some point

"use strict";

/* global console, d3, nv, colorbrewer */

var makeSeries = function(name, color, data) {
    return [ { "key": name, "color": color, "values": data } ];
};

var limitedData = function( d, l ) {
    return d.map( function(d2) { return { "key": d2.key, "color": d2.color, "values": d2.values.slice( 0, l ) }; } );
};

var makeExpandableBarChart = function( selector, seriesName, data, width, height ) {

    var series = makeSeries( seriesName, "steelblue", data );
    console.log(series);
    var limit = Math.min( 7, data.length );

    var chartArea = d3.select( selector )
	.append("svg");

    var chart = function() {
	var chart2 = nv.models.multiBarHorizontalChart()
	    .x( function(d) { return d.label; } ) // curiously x-value represents laber in nvd3
	    .y( function(d) { return d.value; } )
	    .showValues( true )
	    .tooltips( true )
	    .showControls( false )
	    .valueFormat( d3.format("d") )
	    .margin( {top: 20, left: 350, right: 20, bottom: 20} );
	console.log( chart2.multibar.xRange );
	chart2.showLegend( false );

	chart2.yAxis
            .tickFormat(d3.format(",i"));


	chartArea.attr("width", width )
	    .attr("height", height )
	    .datum(limitedData( series, limit ))
	    .call( chart2 );

	nv.utils.windowResize(chart2.update);

	return chart2;
    };

    nv.addGraph( chart );

    // now add the more/less buttons
    var buttonbar = d3.select( selector )
	.append("p");

    buttonbar.append( "input" )
	.attr("id", "More")
	.attr("type", "button")
	.attr("value", "More")
	.on("click", function() {
	    limit = Math.min( limit + 1, series[0].values.length );
	    chartArea.datum( limitedData( series, limit ) )
		//		.attr("height",  height + 50 )
		.call(chart);
	});

    buttonbar.append( "input" )
	.attr("id", "Fewer")
	.attr("type", "button")
	.attr("value", "Fewer")
	.on("click", function() {
	    limit = Math.max( limit - 1, 0 );
	    chartArea.datum( limitedData( series, limit ) )
		//		.attr("height", height-50)
		.call( chart );
	});

};




// CHORD CHART ATTEMPTS

function makeChordChart( selector, matrix, key ) {

    var chord = d3.layout.chord()
	.padding( 0.05 )
	.sortSubgroups( d3.descending )
	.matrix( matrix );

    var width = 960,
	height = 600,
	innerRadius = Math.min( width, height ) * 0.41,
	outerRadius = innerRadius * 1.1;

    var fill = d3.scale.ordinal()
	.domain( d3.range( key.length ) )
	.range( colorbrewer.Spectral[10] );

    var svg = d3.select( selector ).append("svg")
	.attr("width", width )
	.attr("height", height )
	.append("g")
	.attr("id", "circle")
	.attr("transform", "translate(" + width / 2 + "," + height / 2 + ")" );

    svg.append("circle")
	.attr("r", outerRadius )
	.attr("opacity", 0.2);

    function fade(opacity) {
	return function( g, i ) {
	    svg.selectAll(".chord path")
		.filter( function(d) { return d.source.index !== i && d.target.index !== i; } )
		.transition()
		.style("opacity", opacity);
	};
    }

    var groups = svg.selectAll(".group")
	.data( chord.groups )
	.enter().append("g")
	.attr( "class", "group" )
	.on("mouseover", fade(0.1))
	.on("mouseout", fade(1));

    groups.append("title").text( function(d) { return key[d.index]; });

    var groupPath = groups.append("path")
	.attr("id", function(d, i) { return "group" + i; })
	.style("fill", function(d) { return fill(d.index); })
	.style("opacity", 0.8 )
	.attr("d", d3.svg.arc().innerRadius( innerRadius ).outerRadius(outerRadius) );

    var groupdefs = groups.append("defs");

    groupdefs.append("clipPath")
	.attr("id", function(d, i) { return "clip" + i; })
	.append("path")
	.attr("d", d3.svg.arc().innerRadius( innerRadius ).outerRadius(outerRadius) );

    groupdefs.append("path")
	.attr("id", function(d, i) { return "textPath" + i; })
	.attr("d", d3.svg.arc()
	      .innerRadius(innerRadius)
	      .outerRadius(outerRadius)
	      .startAngle( function(d) { return d.startAngle; } )
	      .endAngle( function(d) { return d.endAngle + 1; } )
	);


    // add text label
    var groupText = groups.append("g")
	.attr("clip-path", function(d, i) { return "url(#" + "clip" + i + ")"; } )
	.append("text")
	.attr("x", 6)
	.attr("dy", 15 );

    groupText.append("textPath")
	.attr("xlink:href", function(d, i) { return "#textPath" + i; })
	.text( function(d) { return key[d.index]; });

    // the following will fliter out any labels that won't fit in their arcsn
    /*groupText.filter( function(d,i) { return groupPath[0][i].getTotalLength() / 2 - 16 < this.getComputedTextLength(); })
	.remove()*/

    /*    function groupTicks(d) {
       var k = (d.endAngle - d.startAngle) / d.value;
       return d3.range(0, d.value, 10).map(function(v, i) {
       return {
       angle: v * k + d.startAngle,
       label: "" //i % 1 ? null : v / 10 + ""
       };
       });
    }

      var ticks = svg.append("g").selectAll("g")
	.data(chord.groups)
	.enter().append("g").selectAll("g")
	.data( groupTicks )
	.enter().append("g")
	.attr("transform", function(d) {
	    return "rotate(" + (d.angle*180/Math.PI -90) + ")"
		+ "translate(" + outerRadius + ",0)";
	});

    ticks.append("line")
	.attr("x1",1)
	.attr("y1",0)
	.attr("x2",5)
	.attr("y2",0)
	.style("stroke", "#000");

    ticks.append("text")
	.attr("x", 8)
	.attr("dy", "3.5em")
        .attr("transform", function(d) { return d.angle > Math.PI ? "rotate(180)translate(-16)" : null; })
	.style("text-anchor", function(d) { return d.angle > Math.PI ? "end" : null; })
	.text(function(d) { return d.label; });*/

    svg.append("g")
	.attr("class", "chord")
	.selectAll("path")
	.data(chord.chords)
	.enter().append("path")
	.attr( "class", "chord")
	.attr("d", d3.svg.chord().radius(innerRadius))
	.style("fill", function(d) { return fill(d.target.index); })
	.style("opacity", 1)
	.append("title").text( function(d) { return key[d.source.index]
	    + "-"
	    + key[d.target.index]
	    + ": "
	    + d.source.value
	    + " papers"; } );

    /*    var schord = svg.selectAll(".chord")
	.data( chord.chords )
	.enter().append("path" )
	.attr("class", "chord")
	.style("fill", function(d) { return fill(d.source.index); } )
	.attr("d", d3.svg.chord().radius(innerRadius) )

    schord.append("title").text( function(d) { key[d.source.index]
					       + " and "
					       + key[d.target.index]
					       + " collaborated on "
					       + d.source.value
					       + "papers" } );*/
}

