$(document).ready(function() {
	var counter = 1;
	$("#hockeyRinkHome").click(function(e) {
		// add puck
		var div = $("<div></div>").addClass("puck").offset({top: e.pageY, left: e.pageX});
		div.attr('name', counter).text(counter);
		$(this).append(div);
		// add table row 
		$("#shotInfo").append(tableRow(counter, "Home"));
		counter++;
	});
	
	$("#hockeyRinkAway").click(function(e) {
		// add the puck
		var div = $("<div></div>").addClass("puck").offset({top: e.pageY, left: e.pageX});
		div.attr('name', counter).css('background', 'blue').css('color', 'white').text(counter);
		$(this).append(div);
		// add the table row
		$("#shotInfo").append(tableRow(counter, "Away"));
		counter++;
	});
	
	$(".removeShot").live("click", function(e) {
		var num = $(this).attr('name');
		// remove puck
		$(".puck[name="+num+"]").remove();
		// remove table row
		$("tr[name="+num+"]").remove();
		// renumber
		
		// total counter--
	});
	
	function tableRow(counter, team) {
		var row = "<tr name="+counter+">"
				+"<td>"+counter+"</td>"
				+"<td>"+team+"</td>"
				+"<td><select><option>1</option><option>2</option><option>3</option></td>"
				+"<td></td>"
				+"<td></td>"
				+"<td></td>"
				+"<td><input type=\"button\" value=\"Delete\" class=\"removeShot\" name=\""+counter+"\" /></td>"
				+"</tr>";
		return row;
	}
});
