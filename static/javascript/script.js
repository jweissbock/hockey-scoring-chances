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
	
	$(document).on("click", ".removeShot", function(e) {
		var num = $(this).attr('name');
		// remove puck
		$(".puck[name="+num+"]").remove();
		// remove table row
		$("tr[name="+num+"]").remove();
		// renumber
		
		// total counter--
	});

	$("#saveChances").on('click', function(e) {
		$.jGrowl($("#sGameID").val());
	});

	// when user clicks on the button to enter game ID
	$("#enterGame").click(function(e) {
		var gameID = $("#gameID").val();
		if (isNaN(gameID)) {
			$("#content").hide();
			return;
		}
		gameID = parseInt(gameID);
		gYear = $("#gYear").val()
		$.getJSON("/getGame", { gID: gameID, gYear: gYear }, function(data) {
			if (data[0].success != true) {
				$.jGrowl('Failed to find the game ID');
				$("#content").hide();
				return
			}
			$("#content").show();
			$("#sGameID").val(gameID);
		})
		.fail(function() { alert('failed to AJAX'); });
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
