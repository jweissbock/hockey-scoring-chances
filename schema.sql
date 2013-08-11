drop table if exists chances;
create table chances (
	id integer primary key auto_increment,
	gameid integer not null,
	yearid integer not null,
	team integer not null,
	period integer not null,
	time integer not null,
	comment text,
	posx integer not null,
	posy integer not null
);
ALTER TABLE chances ADD INDEX chanceIndex (gameid, yearid, period, time); 

drop table if exists php;
CREATE TABLE pbp (id integer primary key auto_increment, gid integer, gnumber integer, period integer, timeup integer, timedown integer, event text, description text, v1 integer, v2 integer, v3 integer, v4 integer, v5 integer, v6 integer, h1 integer, h2 integer, h3 integer, h4 integer, h5 integer, h6 integer);
ALTER TABLE php ADD INDEX pbpIndex (gid, period, timedown); 
