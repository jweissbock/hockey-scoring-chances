$(document).ready(function() {
	var counter = 1;
	$("#hockeyRinkHome").click(function(e) {
		var parentOffset = $(this).parent().offset(); 
   		//or $(this).offset(); if you really just want the current element's offset
   		var relX = e.pageX - parentOffset.left;
   		var relY = e.pageY - parentOffset.top;
		// add puck
		var div = $("<div></div>").addClass("puck").offset({top: relY, left: relX});
		div.attr('name', counter).text(counter);
		$(this).append(div);
		// add table row 
		$("#shotInfo").append(tableRow(counter, "Home"));
		counter++;
	});
	
	$("#hockeyRinkAway").click(function(e) {
   		//or $(this).offset(); if you really just want the current element's offset
   		var relX = e.pageX - this.offsetLeft;
   		var relY = e.pageY - this.offsetTop;
		// add the puck
		var div = $("<div></div>").addClass("puck").offset({top: relY, left: relX});
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

	$("#gameReport").on('click', function(e) {
		gameId = $("#sGameID").val();
		
		window.open('/gamereport/'+gameId, '_blank')
	});

	$("#saveChances").on('click', function(e) {
		$.jGrowl("Saving...")
		var data = {};
		data['gameID'] = $("#sGameID").val();
		data['gameYear'] = $("#gYear").val();
		var puckNum = 0;
		$("div.puck").each(function() {
			var position = $(this).offset();
			var puckName = 'puck' + puckNum;
			var puckCounter = $(this).attr('name');
			// need team id, period, time, comment
			data[puckName+'team'] = $("tr[name="+puckCounter+"]").find(".team").text();
			data[puckName+'period'] = $("tr[name="+puckCounter+"]").find(".period").val();
			data[puckName+'time'] = parseInt($("tr[name="+puckCounter+"]").find(".pMin").val())*60 + parseInt($("tr[name="+puckCounter+"]").find(".pSec").val());
			data[puckName+'comment'] = $("tr[name="+puckCounter+"]").find(".comment").val();
			data[puckName+'left'] = position.left;
			data[puckName+'top'] = position.top;
			puckNum++;
		});
		// now we have the data, need to ajax it
		$.getJSON("/saveGame", data, function(data) {
			if (data[0].success == true) {
				$.jGrowl('Saved.');
			} else {
				$.jGrowl('Failed to save.  '+data[0].msg);
			}
		})
		.fail(function() { $.jGrowl('Failed to save data.') });
	});

	// when user clicks on the button to enter game ID
	$("#enterGame").click(function(e) {
		$.jGrowl("LOADING...")
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
			// clear all table items
			// clear all pucks
			$(".puck").remove();
			$(".puckTableRow").remove();
			$("#content").show();
			$("#sGameID").val(gameID);
			// need to clear all pucks on screen atm
			// update overall counter
			// now have all puck data, need to output it on table + image
			counter = 1;
			if (data[0].getChances == true) {
				for (i=0; i<data[0].chances.length; i++) {
					c = data[0].chances[i];
					var e = new jQuery.Event("click");
					e.pageX = c.left;
					e.pageY = c.top;
					if (c.team == 1) { 
						team = "Away"; 
						$("#hockeyRinkAway").trigger(e);
					} else { 
						team = "Home";
						$("#hockeyRinkHome").trigger(e); 
					}
					rowi = i+1
					// change period
					$("tr[name="+rowi+"]").find(".period").val(c.period)
					// change time
					cTimeMin = Math.floor(c.time / 60);
					cTimeSec = c.time % 60;
					$("tr[name="+rowi+"]").find(".pMin").val(cTimeMin);
					$("tr[name="+rowi+"]").find(".pSec").val(cTimeSec);
					// change comment
					$("tr[name="+rowi+"]").find(".comment").val(c.comment)
				}
			}
		})
		.fail(function() { alert('failed to AJAX'); });
	});

	// try and prevent users from entering weird times like 20:53
	$(document).on("change", ".pSec", function(e) {
		if ($(this).val() > 0 && $(this).prev().val() == 20) {
			$(this).val(0);
		}
	});

	$(document).on("change", ".pMin", function(e) {
		if ($(this).val() == 20 && $(this).next().val() > 0) {
			$(this).next().val(0);
		}
	});	
	
	// variables for table
	var periodMinutes = "<select class=\"pMin\">"
	for (i = 20; i >= 0; i--) {
		periodMinutes += "<option value=\""+i+"\">"+i+"</option>"
	}
	periodMinutes += "</select>"

	var pSeconds = "<select class=\"pSec\">"
	for (i = 0; i <= 59; i++) {
		pSeconds += "<option value=\""+i+"\">"+i+"</option>"
	}
	pSeconds += "</select>"

	// find a way to get rid of the for loops each time
	function tableRow(counter, team) {
		var row = "<tr class=\"puckTableRow\" name="+counter+">"
				+"<td>"+counter+"</td>"
				+"<td class=\"team\">"+team+"</td>"
				+"<td><select class=\"period\"><option>1</option><option>2</option><option>3</option></td>"
				+"<td>"+periodMinutes+" : "+pSeconds+"</td>"
				+"<td><input type=\"text\" class=\"comment\" maxlength=\"255\" /></td>"
				+"<td><input type=\"button\" value=\"Delete\" class=\"removeShot\" name=\""+counter+"\" /></td>"
				+"</tr>";
		return row;
	}
});
