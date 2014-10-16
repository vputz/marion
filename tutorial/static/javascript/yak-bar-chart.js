// An attempt to make a reusable bar chart for categorical summary
// data of the CSV/dict form { label : value }
// call via
// myChart = yakBarChart().width(...).height(...) etc
// then
// myChart( selection ) or
// selection.call(myChart)

d3.yak.barChart = function module() {

    var margin = {top:10, right:10, bottom: 10, left:10},
    width = 500,
    height = 500,
    colorScale = d3.scale.category20(),
    xScale = d3.scale.linear(),
    yScale = d3.scale.linear(),
    maxItem = 7,
    barHeightProportion = 0.9,
    makeLabelText = function( el ) {
	el.append( "text" )
	    .attr( "x", 6 )
	    .attr( "y", yScale(1)*barHeightProportion / 2 )
	    .text( function(d) { return d.label; } )
    };

    makeValueText = function( el ) {
	el.append( "text" )
	.attr( "x", function(d) { return xScale(d.value) - 10; } )
	.attr( "y", yScale(1)*barHeightProportion / 2 )
	.text( function(d) { return d.value; } )
    };

    function exports(selection) {
	// generate chart here
	selection.each( function( d, i ) {
	    // 'd' is the data, 'this' is the element; d
	    // should be an ARRAY of { label: string, value: number } 
	    // pairs
	    data = d.slice( 0, Math.min(data.length, maxItem) );
	    // set the X/Y domains/ranges
	    xScale
		.domain( [0, d3.extent( data, function(d) { return d.value; })[1]] )
		.range( [0, width - margin.left - margin.right] );
	    yScale
		.domain( [0, Math.min( maxItem, data.length )] )
		.range( [0, height - margin.top - margin.bottom] );

	    // select the svg element if it exists
	    // note that the first call to data uses [data] to add
	    // a single SVG, but the second call (in "bar = ...")
	    // uses .data(data) to enter the selection with all data
	    // points.  It will be interesting to see what happens
	    // if this is called twice (TODO: test)
	    var svg = d3.select(this).selectAll("svg").data([data]).enter().append("svg");
	    // otherwise create the skeletal chart
	    var bar = svg.selectAll("g").data(data).enter().append("g")
		.attr("transform", function( d,i ) { return "translate(0, " + yScale(i) + ")" } )
	    var barHeight = (yScale( 1 ) - yScale(0)) * barHeightProportion;

	    bar.append("rect")
		.attr("width", function(d) { return xScale(d.value); } )
		.attr( "height", barHeight )
		.style("fill", function(d) { return colorScale( d.label ); } )
		.style("fill-opacity", 1 );

	    makeLabelText( bar );
	    makeValueText( bar );
	});

    }

    exports.makeLabelText = function( _ ) {
	if (!arguments.length) return makeLabelText;
	makeLabelText = _;
	return exports;
    }

    //accessors
    exports.width = function( _ ) {
	if (!arguments.length) return width;
	width = _;
	return exports;
    }

    exports.height = function( _ ) {
	if (!arguments.length) return height;
	height = _;
	return exports;
    }

    exports.margin = function(_) {
	if (!arguments.length) return margin;
	margin = _;
	return exports;
    }

    exports.colorScale = function(_) {
	if ( !arguments.length) return colorScale;
	colorScale = _;
	return exports;
    }

    exports.barHeightProportion = function(_) {
	if ( !arguments.length) return barHeightProportion;
	barHeightProportion = _;
	return exports;
    }

    exports.maxItem = function(_) {
	if ( !arguments.length) return maxItem;
	maxItem = _;
	return exports;
    }

    // and of course we must eventually return the chart
    return exports;
}
