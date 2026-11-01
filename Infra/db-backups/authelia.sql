BEGIN TRANSACTION;
CREATE TABLE authentication_logs (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    successful BOOLEAN NOT NULL,
    banned BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(100) NOT NULL,
    auth_type VARCHAR(8) NOT NULL DEFAULT '1FA',
    remote_ip VARCHAR(39) NULL DEFAULT NULL,
    request_uri TEXT,
    request_method VARCHAR(8) NOT NULL DEFAULT ''
);
INSERT INTO "authentication_logs" VALUES(1,'2026-11-01 11:56:58.076724433+00:00',0,0,'admin','1FA','171.48.81.18','','');
INSERT INTO "authentication_logs" VALUES(2,'2026-11-01 11:57:44.088527041+00:00',1,0,'admin','1FA','171.48.81.18','','');
INSERT INTO "authentication_logs" VALUES(3,'2026-11-01 11:57:51.356398883+00:00',1,0,'user','1FA','171.48.81.18','','');
INSERT INTO "authentication_logs" VALUES(4,'2026-11-01 11:59:01.324533582+00:00',1,0,'admin','1FA','171.48.81.18','','');
INSERT INTO "authentication_logs" VALUES(5,'2026-11-01 12:04:48.857089054+00:00',1,0,'admin','1FA','171.48.81.18','','');
INSERT INTO "authentication_logs" VALUES(6,'2026-11-01 12:20:19.077811148+00:00',1,0,'admin','1FA','171.48.81.18','https://cockpit.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(7,'2026-11-01 12:20:30.518620974+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(8,'2026-11-01 12:20:32.751649636+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(9,'2026-11-01 12:20:34.8808296+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(10,'2026-11-01 12:20:36.959569248+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(11,'2026-11-01 12:20:39.050590492+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(12,'2026-11-01 12:20:41.152515479+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(13,'2026-11-01 12:20:43.290560167+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(14,'2026-11-01 12:20:45.450620263+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(15,'2026-11-01 12:20:47.54603747+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(16,'2026-11-01 12:20:49.750613267+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(17,'2026-11-01 12:20:51.790653992+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(18,'2026-11-01 12:20:53.950629449+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(19,'2026-11-01 12:20:56.023698447+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(20,'2026-11-01 12:20:58.078756635+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(21,'2026-11-01 12:21:00.198671435+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(22,'2026-11-01 12:21:02.351631787+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(23,'2026-11-01 12:21:04.500835944+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(24,'2026-11-01 12:21:06.570659113+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(25,'2026-11-01 12:21:08.611500568+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(26,'2026-11-01 12:21:10.745948107+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(27,'2026-11-01 12:21:12.897563928+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(28,'2026-11-01 12:37:24.330320696+00:00',1,0,'admin','1FA','171.48.81.18','https://cockpit.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(29,'2026-11-01 12:37:37.070563559+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(30,'2026-11-01 12:37:39.200320603+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(31,'2026-11-01 12:37:41.390889464+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(32,'2026-11-01 12:37:43.500228475+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(33,'2026-11-01 12:37:45.670325341+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(34,'2026-11-01 12:37:47.805261075+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(35,'2026-11-01 12:37:49.850260757+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(36,'2026-11-01 12:37:52.000218913+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(37,'2026-11-01 12:37:54.070846278+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(38,'2026-11-01 12:37:56.190349426+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(39,'2026-11-01 12:37:58.295469437+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(40,'2026-11-01 12:38:00.811229497+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(41,'2026-11-01 12:38:03.315580528+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(42,'2026-11-01 12:38:05.631281294+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(43,'2026-11-01 12:38:07.676381657+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(44,'2026-11-01 12:38:09.865206902+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(45,'2026-11-01 12:38:11.91612912+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(46,'2026-11-01 12:38:13.955358348+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(47,'2026-11-01 12:38:16.070644017+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(48,'2026-11-01 12:38:18.326492416+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(49,'2026-11-01 12:38:20.575414469+00:00',0,0,'','1FA','171.48.81.18','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(50,'2026-11-01 12:56:30.818895518+00:00',1,0,'admin','1FA','130.210.25.74','','');
INSERT INTO "authentication_logs" VALUES(51,'2026-11-01 14:12:46.779932905+00:00',1,0,'admin','1FA','171.48.81.18','https://mail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(52,'2026-11-01 14:16:16.003828099+00:00',1,0,'admin','1FA','171.48.81.18','https://mail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(53,'2026-11-01 20:36:28.242006872+00:00',1,0,'admin','1FA','106.192.50.65','https://mail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(54,'2026-11-01 20:51:36.856391062+00:00',1,0,'admin','1FA','130.210.25.74','','');
INSERT INTO "authentication_logs" VALUES(55,'2026-11-01 20:56:26.212826802+00:00',1,0,'user','1FA','106.192.50.65','https://mail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(56,'2026-11-01 20:59:58.630008857+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(57,'2026-11-01 21:00:00.780696206+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(58,'2026-11-01 21:00:02.894976415+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(59,'2026-11-01 21:00:04.980343992+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(60,'2026-11-01 21:00:07.035115563+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(61,'2026-11-01 21:00:09.144993211+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(62,'2026-11-01 21:00:11.209988158+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(63,'2026-11-01 21:00:13.385041297+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(64,'2026-11-01 21:00:15.525081027+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(65,'2026-11-01 21:00:17.640014323+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(66,'2026-11-01 21:00:19.735023432+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(67,'2026-11-01 21:00:21.985148394+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(68,'2026-11-01 21:00:24.030067354+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(69,'2026-11-01 21:00:26.075025595+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(70,'2026-11-01 21:00:28.120700882+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(71,'2026-11-01 21:00:30.275188949+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(72,'2026-11-01 21:00:42.416652674+00:00',1,0,'admin','1FA','130.210.25.74','','');
INSERT INTO "authentication_logs" VALUES(73,'2026-11-01 21:01:00.185976941+00:00',0,0,'admin','1FA','106.192.50.65','https://mail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(74,'2026-11-01 21:01:05.734878139+00:00',0,0,'admin','1FA','106.192.50.65','https://mail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(75,'2026-11-01 21:01:30.351855671+00:00',1,0,'admin','1FA','130.210.25.74','','');
INSERT INTO "authentication_logs" VALUES(76,'2026-11-01 21:01:36.933154389+00:00',0,0,'admin','1FA','106.192.50.65','https://mail.rohan.run.place/view/41Ho0p5fiNMMsKOvFx9SIh','GET');
INSERT INTO "authentication_logs" VALUES(77,'2026-11-01 21:03:36.411305427+00:00',0,0,'admin','1FA','106.192.50.65','https://user.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(78,'2026-11-01 21:03:46.486681443+00:00',1,0,'admin','1FA','106.192.50.65','https://user.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(79,'2026-11-01 21:06:24.316432723+00:00',1,0,'jatin','1FA','106.192.50.65','https://cockpit.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(80,'2026-11-01 21:16:49.026737098+00:00',1,0,'admin','1FA','106.192.50.65','https://user.rohan.run.place/group-attributes','GET');
INSERT INTO "authentication_logs" VALUES(81,'2026-11-01 21:17:47.59028571+00:00',1,0,'admin','1FA','106.192.50.65','https://user.rohan.run.place/users','GET');
INSERT INTO "authentication_logs" VALUES(82,'2026-11-01 21:21:42.173805056+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(83,'2026-11-01 21:21:44.213693729+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(84,'2026-11-01 21:21:46.367776117+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(85,'2026-11-01 21:21:48.479718108+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(86,'2026-11-01 21:21:50.66592936+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(87,'2026-11-01 21:21:52.816426714+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(88,'2026-11-01 21:21:54.912115511+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(89,'2026-11-01 21:21:57.063040428+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(90,'2026-11-01 21:21:59.164002635+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(91,'2026-11-01 21:22:01.319134272+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(92,'2026-11-01 21:22:03.408219806+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(93,'2026-11-01 21:22:05.508687647+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(94,'2026-11-01 21:22:07.558626611+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(95,'2026-11-01 21:22:09.639069983+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(96,'2026-11-01 21:22:11.711987003+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(97,'2026-11-01 21:22:13.754351736+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(98,'2026-11-01 21:22:15.815136521+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(99,'2026-11-01 21:22:17.908305052+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(100,'2026-11-01 21:22:20.004212368+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(101,'2026-11-01 21:22:22.047618629+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(102,'2026-11-01 21:22:24.163969778+00:00',0,0,'','1FA','106.192.50.65','https://cockpit.rohan.run.place/cockpit/login','GET');
INSERT INTO "authentication_logs" VALUES(103,'2026-11-01 21:25:06.997093736+00:00',0,0,'admin','1FA','106.192.50.65','https://mail.rohan.run.place/view/41Ho0p5fiNMMsKOvFx9SIh','GET');
INSERT INTO "authentication_logs" VALUES(104,'2026-11-01 21:25:13.880681607+00:00',0,0,'admin','1FA','106.192.50.65','https://mail.rohan.run.place/view/41Ho0p5fiNMMsKOvFx9SIh','GET');
INSERT INTO "authentication_logs" VALUES(105,'2026-11-01 21:25:17.99444859+00:00',1,0,'admin','1FA','106.192.50.65','https://mail.rohan.run.place/view/41Ho0p5fiNMMsKOvFx9SIh','GET');
INSERT INTO "authentication_logs" VALUES(106,'2026-11-01 21:25:42.467783627+00:00',1,0,'admin','1FA','106.192.50.65','https://webmail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(107,'2026-11-01 21:30:42.425145564+00:00',1,0,'admin','1FA','106.192.50.65','https://webmail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(108,'2026-11-01 21:39:30.397253602+00:00',1,0,'jatin','1FA','106.192.50.65','https://webmail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(109,'2026-11-01 21:41:46.060124487+00:00',1,0,'admin','1FA','172.18.0.1','','');
INSERT INTO "authentication_logs" VALUES(110,'2026-11-01 21:42:02.095265235+00:00',1,0,'admin','1FA','172.18.0.1','','');
INSERT INTO "authentication_logs" VALUES(111,'2026-11-01 21:42:12.974800475+00:00',1,0,'admin','1FA','172.18.0.1','','');
INSERT INTO "authentication_logs" VALUES(112,'2026-11-01 21:42:22.313486307+00:00',1,0,'admin','1FA','172.18.0.1','','');
INSERT INTO "authentication_logs" VALUES(113,'2026-11-01 21:42:31.299425824+00:00',1,0,'admin','1FA','172.18.0.1','','');
INSERT INTO "authentication_logs" VALUES(114,'2026-11-01 21:42:47.371612637+00:00',1,0,'admin','1FA','172.18.0.1','','');
INSERT INTO "authentication_logs" VALUES(115,'2026-11-01 21:44:05.699799534+00:00',1,0,'jatin','1FA','106.192.50.65','https://webmail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(116,'2026-11-01 21:44:17.419485104+00:00',1,0,'admin','1FA','106.192.50.65','https://user.rohan.run.place/groups','GET');
INSERT INTO "authentication_logs" VALUES(117,'2026-11-01 21:47:11.517964107+00:00',0,0,'jatin','1FA','172.18.0.1','','');
INSERT INTO "authentication_logs" VALUES(118,'2026-11-01 21:47:20.468477205+00:00',1,0,'admin','1FA','172.18.0.1','','');
INSERT INTO "authentication_logs" VALUES(119,'2026-11-01 21:48:33.620997389+00:00',1,0,'jatin','1FA','106.192.50.65','','');
INSERT INTO "authentication_logs" VALUES(120,'2026-11-01 21:50:56.489360533+00:00',1,0,'jatin','1FA','106.192.50.65','https://webmail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(121,'2026-11-01 21:54:52.87308917+00:00',1,0,'admin','1FA','106.192.50.65','https://webmail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(122,'2026-11-01 21:59:32.931648999+00:00',0,0,'jatin','1FA','106.192.50.65','https://webmail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(123,'2026-11-01 21:59:38.520391371+00:00',1,0,'jatin','1FA','106.192.50.65','https://webmail.rohan.run.place/','GET');
INSERT INTO "authentication_logs" VALUES(124,'2026-11-01 22:00:45.734537512+00:00',1,0,'jatin','1FA','106.192.50.65','https://webmail.rohan.run.place/','GET');
CREATE TABLE banned_ip (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires TIMESTAMP NULL DEFAULT NULL,
    expired TIMESTAMP NULL DEFAULT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    ip VARCHAR(39) NOT NULL,
    source VARCHAR(10) NOT NULL,
    reason VARCHAR(100) NULL DEFAULT NULL
);
CREATE TABLE banned_user (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires TIMESTAMP NULL DEFAULT NULL,
    expired TIMESTAMP NULL DEFAULT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(100) NOT NULL,
    source VARCHAR(10) NOT NULL,
    reason VARCHAR(100) NULL DEFAULT NULL
);
CREATE TABLE cached_data (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL,
    name VARCHAR(20) NOT NULL,
    encrypted BOOLEAN NOT NULL DEFAULT FALSE,
    value BLOB NOT NULL
);
CREATE TABLE duo_devices (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) NOT NULL,
    device VARCHAR(32) NOT NULL,
    method VARCHAR(16) NOT NULL
);
CREATE TABLE encryption (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100),
    value BLOB NOT NULL
);
INSERT INTO "encryption" VALUES(1,'check',X'D7B651103A9077E2947CEC89337090DB94A104327CC9A94BBBC608273C03C5D3298A0CB38146F0B97135A570FFDFFDB88A7AEC1E382C08805280E83831553C08');
INSERT INTO "encryption" VALUES(2,'hmac_key_otc',X'ACF5B2C0912BD0EC5570FCC75ACE4B548D0B12CE79E13BB8B44E4A13636FFAF8702E3B3128C3BCC6C894DE0A5D487A1FC24B3B40AA5B0A099949AB580989C78AF0589596385094AC8418B87175EFA42B4B4B60FCAA883C9AE9BC1B22E5975DA20F90243191F70BE01449CD8B881464E509A3418B1DC80A81BF15762432799DEEEA3C128516A22A32BA44D6721F7B667CE4E02760EF96EBFAF6A5BADE');
INSERT INTO "encryption" VALUES(3,'hmac_key_otp',X'32C5986166A8CABB1445DB1C884AF69FD9090B518C08097083341128324132F4F0EEAC0A9DCA548CB53A55AAE6237BF2C6ACA1E49030A7EB226F6B3D20DE8B9A3AADBA999D36D0DC3BBF5C3491D080C963306ACCE299256276774659');
CREATE TABLE identity_verification (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    jti VARCHAR(36),
    iat DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    issued_ip VARCHAR(39) NOT NULL,
    exp DATETIME NOT NULL,
    username VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    consumed DATETIME NULL DEFAULT NULL,
    consumed_ip VARCHAR(39) NULL DEFAULT NULL
, revoked DATETIME NULL DEFAULT NULL, revoked_ip VARCHAR(39) NULL DEFAULT NULL);
INSERT INTO "identity_verification" VALUES(1,'603c07a1-ec21-4cca-b576-5887eb755831','2026-11-01 12:39:55.231881813+00:00','171.48.81.18','2026-11-01 12:44:55.231881933+00:00','admin','ResetPassword',NULL,NULL,NULL,NULL);
INSERT INTO "identity_verification" VALUES(2,'2fbf5768-5e2f-42a6-9409-c25db20616f1','2026-11-01 21:00:35.128252862+00:00','106.192.50.65','2026-11-01 21:05:35.128252942+00:00','admin','ResetPassword',NULL,NULL,NULL,NULL);
CREATE TABLE migrations (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    applied DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    version_before INTEGER NULL DEFAULT NULL,
    version_after INTEGER NOT NULL,
    application_version VARCHAR(128) NOT NULL
);
INSERT INTO "migrations" VALUES(1,'2026-11-01 11:47:39.598276709+00:00',0,1,'v4.39.28');
INSERT INTO "migrations" VALUES(2,'2026-11-01 11:47:39.599270119+00:00',1,2,'v4.39.28');
INSERT INTO "migrations" VALUES(3,'2026-11-01 11:47:39.599750323+00:00',2,3,'v4.39.28');
INSERT INTO "migrations" VALUES(4,'2026-11-01 11:47:39.600785293+00:00',3,4,'v4.39.28');
INSERT INTO "migrations" VALUES(5,'2026-11-01 11:47:39.607328675+00:00',4,5,'v4.39.28');
INSERT INTO "migrations" VALUES(6,'2026-11-01 11:47:39.608523566+00:00',5,6,'v4.39.28');
INSERT INTO "migrations" VALUES(7,'2026-11-01 11:47:39.622755861+00:00',6,7,'v4.39.28');
INSERT INTO "migrations" VALUES(8,'2026-11-01 11:47:39.622892662+00:00',7,8,'v4.39.28');
INSERT INTO "migrations" VALUES(9,'2026-11-01 11:47:39.622951902+00:00',8,9,'v4.39.28');
INSERT INTO "migrations" VALUES(10,'2026-11-01 11:47:39.623347226+00:00',9,10,'v4.39.28');
INSERT INTO "migrations" VALUES(11,'2026-11-01 11:47:39.62372035+00:00',10,11,'v4.39.28');
INSERT INTO "migrations" VALUES(12,'2026-11-01 11:47:39.624040473+00:00',11,12,'v4.39.28');
INSERT INTO "migrations" VALUES(13,'2026-11-01 11:47:39.624138994+00:00',12,13,'v4.39.28');
INSERT INTO "migrations" VALUES(14,'2026-11-01 11:47:39.62482188+00:00',13,14,'v4.39.28');
INSERT INTO "migrations" VALUES(15,'2026-11-01 11:47:39.624959281+00:00',14,15,'v4.39.28');
INSERT INTO "migrations" VALUES(16,'2026-11-01 11:47:39.627553746+00:00',15,16,'v4.39.28');
INSERT INTO "migrations" VALUES(17,'2026-11-01 11:47:39.62905952+00:00',16,17,'v4.39.28');
INSERT INTO "migrations" VALUES(18,'2026-11-01 11:47:39.629297882+00:00',17,18,'v4.39.28');
INSERT INTO "migrations" VALUES(19,'2026-11-01 11:47:39.629833767+00:00',18,19,'v4.39.28');
INSERT INTO "migrations" VALUES(20,'2026-11-01 11:47:39.63015073+00:00',19,20,'v4.39.28');
INSERT INTO "migrations" VALUES(21,'2026-11-01 11:47:39.63016713+00:00',20,21,'v4.39.28');
INSERT INTO "migrations" VALUES(22,'2026-11-01 11:47:39.630604295+00:00',21,22,'v4.39.28');
INSERT INTO "migrations" VALUES(23,'2026-11-01 11:47:39.630618655+00:00',22,23,'v4.39.28');
INSERT INTO "migrations" VALUES(24,'2026-11-01 11:47:39.633934486+00:00',23,24,'v4.39.28');
INSERT INTO "migrations" VALUES(25,'2026-11-01 11:47:39.633967246+00:00',24,25,'v4.39.28');
INSERT INTO "migrations" VALUES(26,'2026-11-01 11:47:39.634294449+00:00',25,26,'v4.39.28');
INSERT INTO "migrations" VALUES(27,'2026-11-01 11:47:39.634818014+00:00',26,27,'v4.39.28');
INSERT INTO "migrations" VALUES(28,'2026-11-01 11:47:39.634840055+00:00',27,28,'v4.39.28');
INSERT INTO "migrations" VALUES(29,'2026-11-01 11:47:39.643556697+00:00',28,29,'v4.39.28');
CREATE TABLE oauth2_access_token_session (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    challenge_id CHAR(36) NULL DEFAULT NULL,
    request_id VARCHAR(40) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    signature VARCHAR(768) NOT NULL,
    subject CHAR(36) NULL DEFAULT NULL,
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    requested_scopes TEXT NOT NULL,
    granted_scopes TEXT NOT NULL,
    requested_audience TEXT NULL DEFAULT '',
    granted_audience TEXT NULL DEFAULT '',
    active BOOLEAN NOT NULL DEFAULT FALSE,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    form_data TEXT NOT NULL,
    session_data BLOB NOT NULL, requested_resource TEXT NULL DEFAULT '', granted_resource TEXT NULL DEFAULT '',
    CONSTRAINT oauth2_access_token_session_challenge_id_fkey
        FOREIGN KEY (challenge_id)
            REFERENCES oauth2_consent_session (challenge_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT oauth2_access_token_session_subject_fkey
        FOREIGN KEY (subject)
            REFERENCES user_opaque_identifier (identifier) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE TABLE oauth2_authorization_code_session (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    challenge_id CHAR(36) NOT NULL,
    request_id VARCHAR(40) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    signature VARCHAR(255) NOT NULL,
    subject CHAR(36) NOT NULL,
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    requested_scopes TEXT NOT NULL,
    granted_scopes TEXT NOT NULL,
    requested_audience TEXT NULL DEFAULT '',
    granted_audience TEXT NULL DEFAULT '',
    active BOOLEAN NOT NULL DEFAULT FALSE,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    form_data TEXT NOT NULL,
    session_data BLOB NOT NULL, requested_resource TEXT NULL DEFAULT '', granted_resource TEXT NULL DEFAULT '',
    CONSTRAINT oauth2_authorization_code_session_challenge_id_fkey
        FOREIGN KEY (challenge_id)
            REFERENCES oauth2_consent_session (challenge_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT oauth2_authorization_code_session_subject_fkey
        FOREIGN KEY (subject)
            REFERENCES user_opaque_identifier (identifier) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE TABLE oauth2_blacklisted_jti (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    signature VARCHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE oauth2_consent_preconfiguration (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    client_id VARCHAR(255) NOT NULL,
    subject CHAR(36) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NULL DEFAULT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    scopes TEXT NOT NULL,
    audience TEXT NULL, requested_claims TEXT NULL, signature_claims CHAR(64) NULL, granted_claims TEXT DEFAULT '', resource TEXT NULL,
    CONSTRAINT oauth2_consent_preconfiguration_subject_fkey
        FOREIGN KEY (subject)
            REFERENCES user_opaque_identifier (identifier) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE TABLE oauth2_consent_session (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    challenge_id CHAR(36) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    subject CHAR(36) NULL DEFAULT NULL,
    authorized BOOLEAN NOT NULL DEFAULT FALSE,
    granted BOOLEAN NOT NULL DEFAULT FALSE,
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    responded_at DATETIME NULL DEFAULT NULL,
    form_data TEXT NOT NULL,
    requested_scopes TEXT NOT NULL,
    granted_scopes TEXT NOT NULL,
    requested_audience TEXT NULL DEFAULT '',
    granted_audience TEXT NULL DEFAULT '',
    preconfiguration INTEGER NULL DEFAULT NULL, granted_claims TEXT NULL, expires_at TIMESTAMP NOT NULL DEFAULT '2000-01-01 00:00:00.000000000+00:00', requested_resource TEXT NULL DEFAULT '', granted_resource TEXT NULL DEFAULT '',
    CONSTRAINT oauth2_consent_session_subject_fkey
        FOREIGN KEY (subject)
            REFERENCES user_opaque_identifier (identifier) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT oauth2_consent_session_preconfiguration_fkey
        FOREIGN KEY (preconfiguration)
            REFERENCES oauth2_consent_preconfiguration (id) ON UPDATE CASCADE ON DELETE CASCADE
);
CREATE TABLE oauth2_device_code_session (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    challenge_id CHAR(36) NULL DEFAULT NULL,
    request_id VARCHAR(40) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    signature VARCHAR(255) NOT NULL,
    user_code_signature VARCHAR(255) NOT NULL,
    status INTEGER NOT NULL,
    subject CHAR(36) NULL DEFAULT NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    requested_scopes TEXT NOT NULL,
    granted_scopes TEXT NOT NULL,
    requested_audience TEXT NULL DEFAULT '',
    granted_audience TEXT NULL DEFAULT '',
    active BOOLEAN NOT NULL DEFAULT FALSE,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    form_data TEXT NOT NULL,
    session_data BLOB NOT NULL, requested_resource TEXT NULL DEFAULT '', granted_resource TEXT NULL DEFAULT '',
    CONSTRAINT oauth2_device_code_session_challenge_id_fkey
        FOREIGN KEY (challenge_id)
            REFERENCES oauth2_consent_session (challenge_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT oauth2_device_code_session_subject_fkey
        FOREIGN KEY (subject)
            REFERENCES user_opaque_identifier (identifier) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE TABLE oauth2_openid_connect_session (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    challenge_id CHAR(36) NOT NULL,
    request_id VARCHAR(40) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    signature VARCHAR(255) NOT NULL,
    subject CHAR(36) NOT NULL,
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    requested_scopes TEXT NOT NULL,
    granted_scopes TEXT NOT NULL,
    requested_audience TEXT NULL DEFAULT '',
    granted_audience TEXT NULL DEFAULT '',
    active BOOLEAN NOT NULL DEFAULT FALSE,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    form_data TEXT NOT NULL,
    session_data BLOB NOT NULL, requested_resource TEXT NULL DEFAULT '', granted_resource TEXT NULL DEFAULT '',
    CONSTRAINT oauth2_openid_connect_session_challenge_id_fkey
        FOREIGN KEY (challenge_id)
            REFERENCES oauth2_consent_session (challenge_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT oauth2_openid_connect_session_subject_fkey
        FOREIGN KEY (subject)
            REFERENCES user_opaque_identifier (identifier) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE TABLE oauth2_par_context (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    signature VARCHAR(255) NOT NULL,
    request_id VARCHAR(40) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    scopes TEXT NOT NULL,
    audience TEXT NOT NULL,
    handled_response_types TEXT NOT NULL,
    response_mode TEXT NOT NULL,
    response_mode_default TEXT NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    form_data TEXT NOT NULL,
    session_data BLOB NOT NULL
, resource TEXT NOT NULL DEFAULT '');
CREATE TABLE oauth2_pkce_request_session (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    challenge_id CHAR(36) NOT NULL,
    request_id VARCHAR(40) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    signature VARCHAR(255) NOT NULL,
    subject CHAR(36) NOT NULL,
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    requested_scopes TEXT NOT NULL,
    granted_scopes TEXT NOT NULL,
    requested_audience TEXT NULL DEFAULT '',
    granted_audience TEXT NULL DEFAULT '',
    active BOOLEAN NOT NULL DEFAULT FALSE,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    form_data TEXT NOT NULL,
    session_data BLOB NOT NULL, requested_resource TEXT NULL DEFAULT '', granted_resource TEXT NULL DEFAULT '',
    CONSTRAINT oauth2_pkce_request_session_challenge_id_fkey
        FOREIGN KEY (challenge_id)
            REFERENCES oauth2_consent_session (challenge_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT oauth2_pkce_request_session_subject_fkey
        FOREIGN KEY (subject)
            REFERENCES user_opaque_identifier (identifier) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE TABLE oauth2_refresh_token_session (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    challenge_id CHAR(36) NOT NULL,
    request_id VARCHAR(40) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    signature VARCHAR(255) NOT NULL,
    subject CHAR(36) NOT NULL,
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    requested_scopes TEXT NOT NULL,
    granted_scopes TEXT NOT NULL,
    requested_audience TEXT NULL DEFAULT '',
    granted_audience TEXT NULL DEFAULT '',
    active BOOLEAN NOT NULL DEFAULT FALSE,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    form_data TEXT NOT NULL,
    session_data BLOB NOT NULL, access_signature VARCHAR(768) NOT NULL DEFAULT '', requested_resource TEXT NULL DEFAULT '', granted_resource TEXT NULL DEFAULT '',
    CONSTRAINT oauth2_refresh_token_session_challenge_id_fkey
        FOREIGN KEY (challenge_id)
            REFERENCES oauth2_consent_session (challenge_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT oauth2_refresh_token_session_subject_fkey
        FOREIGN KEY (subject)
            REFERENCES user_opaque_identifier (identifier) ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE TABLE one_time_code (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    public_id CHAR(36) NOT NULL,
    signature VARCHAR(128) NOT NULL,
    issued DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    issued_ip VARCHAR(39) NOT NULL,
    expires DATETIME NOT NULL,
    username VARCHAR(100) NOT NULL,
    intent VARCHAR(100) NOT NULL,
    consumed DATETIME NULL DEFAULT NULL,
    consumed_ip VARCHAR(39) NULL DEFAULT NULL,
    revoked DATETIME NULL DEFAULT NULL,
    revoked_ip VARCHAR(39) NULL DEFAULT NULL,
    code BLOB NOT NULL
);
CREATE TABLE totp_configurations (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME NULL DEFAULT NULL,
    username VARCHAR(100) NOT NULL,
    issuer VARCHAR(100),
    algorithm VARCHAR(6) NOT NULL DEFAULT 'SHA1',
    digits INTEGER NOT NULL DEFAULT 6,
    period INTEGER NOT NULL DEFAULT 30,
    secret BLOB NOT NULL
);
CREATE TABLE totp_history (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    username VARCHAR(100) NOT NULL,
    step CHAR(64) NOT NULL
);
CREATE TABLE user_opaque_identifier (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    service VARCHAR(20) NOT NULL,
    sector_id VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL,
    identifier CHAR(36) NOT NULL
);
CREATE TABLE user_preferences (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) NOT NULL,
    second_factor_method VARCHAR(11) NOT NULL
);
INSERT INTO "user_preferences" VALUES(2,'admin','totp');
INSERT INTO "user_preferences" VALUES(4,'jatin','totp');
CREATE TABLE webauthn_credentials (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME NULL DEFAULT NULL,
    rpid VARCHAR(512) NOT NULL,
    username VARCHAR(100) NOT NULL,
    description VARCHAR(64) NOT NULL,
    kid VARCHAR(512) NOT NULL,
    aaguid CHAR(36) NULL,
    attestation_format VARCHAR(32),
    attachment VARCHAR(64),
    transport VARCHAR(64) DEFAULT '',
    sign_count INTEGER DEFAULT 0,
    clone_warning BOOLEAN NOT NULL DEFAULT FALSE,
    legacy BOOLEAN NOT NULL DEFAULT FALSE,
    discoverable BOOLEAN NOT NULL,
    present BOOLEAN NOT NULL DEFAULT FALSE,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    backup_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    backup_state BOOLEAN NOT NULL DEFAULT FALSE,
    public_key BLOB NOT NULL
, attestation BLOB NULL DEFAULT NULL, attestation_type VARCHAR(32) NOT NULL DEFAULT '');
CREATE TABLE webauthn_users (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    rpid VARCHAR(512) NOT NULL,
    username VARCHAR(100) NOT NULL,
    userid CHAR(64) NOT NULL
);
CREATE UNIQUE INDEX identity_verification_jti_key ON identity_verification (jti);
CREATE UNIQUE INDEX totp_configurations_username_key ON totp_configurations (username);
CREATE UNIQUE INDEX duo_devices_username_key ON duo_devices (username);
CREATE UNIQUE INDEX user_preferences_username_key ON user_preferences (username);
CREATE UNIQUE INDEX encryption_name_key ON encryption (name);
CREATE UNIQUE INDEX user_opaque_identifier_lookup_key ON user_opaque_identifier (service, sector_id, username);
CREATE UNIQUE INDEX user_opaque_identifier_identifier_key ON user_opaque_identifier (identifier);
CREATE INDEX authentication_logs_username_idx ON authentication_logs (time, username, auth_type);
CREATE INDEX authentication_logs_remote_ip_idx ON authentication_logs (time, remote_ip, auth_type);
CREATE UNIQUE INDEX oauth2_blacklisted_jti_signature_key ON oauth2_blacklisted_jti (signature);
CREATE UNIQUE INDEX oauth2_par_context_signature_key ON oauth2_par_context (signature);
CREATE UNIQUE INDEX webauthn_credentials_kid_key ON webauthn_credentials (kid);
CREATE UNIQUE INDEX webauthn_credentials_lookup_key ON webauthn_credentials (rpid, username, description);
CREATE UNIQUE INDEX webauthn_users_lookup_key ON webauthn_users (rpid, username);
CREATE UNIQUE INDEX one_time_code_lookup_key ON one_time_code (signature, username);
CREATE UNIQUE INDEX totp_history_lookup_key ON totp_history (username, step);
CREATE UNIQUE INDEX oauth2_consent_session_challenge_id_key ON oauth2_consent_session (challenge_id);
CREATE INDEX oauth2_authorization_code_session_request_id_idx ON oauth2_authorization_code_session (request_id);
CREATE INDEX oauth2_authorization_code_session_client_id_idx ON oauth2_authorization_code_session (client_id);
CREATE INDEX oauth2_authorization_code_session_client_id_subject_idx ON oauth2_authorization_code_session (client_id, subject);
CREATE INDEX oauth2_access_token_session_request_id_idx ON oauth2_access_token_session (request_id);
CREATE INDEX oauth2_access_token_session_client_id_idx ON oauth2_access_token_session (client_id);
CREATE INDEX oauth2_access_token_session_client_id_subject_idx ON oauth2_access_token_session (client_id, subject);
CREATE INDEX oauth2_refresh_token_session_request_id_idx ON oauth2_refresh_token_session (request_id);
CREATE INDEX oauth2_refresh_token_session_client_id_idx ON oauth2_refresh_token_session (client_id);
CREATE INDEX oauth2_refresh_token_session_client_id_subject_idx ON oauth2_refresh_token_session (client_id, subject);
CREATE INDEX oauth2_pkce_request_session_request_id_idx ON oauth2_pkce_request_session (request_id);
CREATE INDEX oauth2_pkce_request_session_client_id_idx ON oauth2_pkce_request_session (client_id);
CREATE INDEX oauth2_pkce_request_session_client_id_subject_idx ON oauth2_pkce_request_session (client_id, subject);
CREATE INDEX oauth2_openid_connect_session_request_id_idx ON oauth2_openid_connect_session (request_id);
CREATE INDEX oauth2_openid_connect_session_client_id_idx ON oauth2_openid_connect_session (client_id);
CREATE INDEX oauth2_openid_connect_session_client_id_subject_idx ON oauth2_openid_connect_session (client_id, subject);
CREATE INDEX oauth2_device_code_session_request_id_idx ON oauth2_device_code_session (request_id);
CREATE INDEX oauth2_device_code_session_client_id_idx ON oauth2_device_code_session (client_id);
CREATE INDEX oauth2_device_code_session_client_id_subject_idx ON oauth2_device_code_session (client_id, subject);
CREATE UNIQUE INDEX cached_data_name_key ON cached_data (name);
CREATE INDEX banned_user_username_idx ON banned_user (username);
CREATE INDEX banned_user_lookup_idx ON banned_user (username, revoked, expires, expired);
CREATE INDEX banned_user_list_idx ON banned_user (revoked, expires, expired);
CREATE INDEX banned_ip_ip_idx ON banned_ip (ip);
CREATE INDEX banned_ip_lookup_idx ON banned_ip (ip, revoked, expires, expired);
CREATE INDEX banned_ip_list_idx ON banned_ip (revoked, expires, expired);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('identity_verification',2);
INSERT INTO "sqlite_sequence" VALUES('totp_configurations',0);
INSERT INTO "sqlite_sequence" VALUES('duo_devices',0);
INSERT INTO "sqlite_sequence" VALUES('user_preferences',4);
INSERT INTO "sqlite_sequence" VALUES('encryption',3);
INSERT INTO "sqlite_sequence" VALUES('user_opaque_identifier',0);
INSERT INTO "sqlite_sequence" VALUES('authentication_logs',124);
INSERT INTO "sqlite_sequence" VALUES('migrations',29);
INSERT INTO "sqlite_sequence" VALUES('oauth2_blacklisted_jti',0);
INSERT INTO "sqlite_sequence" VALUES('oauth2_consent_preconfiguration',0);
INSERT INTO "sqlite_sequence" VALUES('webauthn_credentials',0);
INSERT INTO "sqlite_sequence" VALUES('oauth2_consent_session',0);
INSERT INTO "sqlite_sequence" VALUES('oauth2_authorization_code_session',0);
INSERT INTO "sqlite_sequence" VALUES('oauth2_access_token_session',0);
INSERT INTO "sqlite_sequence" VALUES('oauth2_refresh_token_session',0);
INSERT INTO "sqlite_sequence" VALUES('oauth2_pkce_request_session',0);
INSERT INTO "sqlite_sequence" VALUES('oauth2_openid_connect_session',0);
COMMIT;
