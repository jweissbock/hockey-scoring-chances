drop table if exists chances;
create table chances (
	id integer primary key autoincrement,
	gameid integer not null,
	yearid integer not null,
	team integer not null,
	period integer not null,
	time integer not null,
	shottype integer not null,
	comment integer not null,
	posx integer not null,
	posy integer not null
);
