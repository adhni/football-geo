(function () {
  "use strict";

  // English is the source text in the static page and the dashboard renderer.
  // Each row is [English, Spanish, French, Arabic, Indonesian].
  const rows = [
    ["Language", "Idioma", "Langue", "اللغة", "Bahasa"],
    ["Choose a sport", "Elegir deporte", "Choisir un sport", "اختر رياضة", "Pilih olahraga"],
    ["Football Talent Geography home", "Inicio de Football Geo", "Accueil de Football Geo", "الصفحة الرئيسية لفوتبول جيو", "Beranda Football Geo"],
    ["Dashboard filters", "Filtros del panel", "Filtres du tableau de bord", "مرشحات اللوحة", "Filter dasbor"],
    ["Dashboard views", "Vistas del panel", "Vues du tableau de bord", "عروض اللوحة", "Tampilan dasbor"],
    ["Map exploration controls", "Controles del mapa", "Commandes de la carte", "أدوات استكشاف الخريطة", "Kontrol eksplorasi peta"],
    ["Map view", "Vista del mapa", "Vue de la carte", "عرض الخريطة", "Tampilan peta"],
    ["Map legend", "Leyenda del mapa", "Légende de la carte", "مفتاح الخريطة", "Legenda peta"],
    ["Close top locations", "Cerrar lugares principales", "Fermer les principaux lieux", "إغلاق أبرز الأماكن", "Tutup lokasi teratas"],
    ["Interactive map of player birthplaces", "Mapa interactivo de lugares de nacimiento", "Carte interactive des lieux de naissance", "خريطة تفاعلية لأماكن ميلاد اللاعبين", "Peta interaktif tempat lahir pemain"],
    ["Players per million people colour scale", "Escala de jugadores por millón de habitantes", "Échelle des joueurs par million d’habitants", "مقياس ألوان اللاعبين لكل مليون نسمة", "Skala warna pemain per juta penduduk"],
    ["Population area size", "Tamaño de zona poblacional", "Taille des zones de population", "حجم منطقة السكان", "Ukuran wilayah penduduk"],
    ["Current selection summary", "Resumen de la selección actual", "Résumé de la sélection actuelle", "ملخص الاختيار الحالي", "Ringkasan pilihan saat ini"],
    ["Age chart view", "Vista del gráfico de edades", "Vue du graphique des âges", "عرض مخطط الأعمار", "Tampilan bagan usia"],
    ["Age comparison level", "Nivel de comparación de edades", "Niveau de comparaison des âges", "مستوى مقارنة الأعمار", "Tingkat perbandingan usia"],
    ["Search player or birthplace", "Buscar jugador o lugar de nacimiento", "Chercher un joueur ou un lieu de naissance", "ابحث عن لاعب أو مكان ميلاد", "Cari pemain atau tempat lahir"],
    ["Try London, Paris, Dakar…", "Prueba Londres, París, Dakar…", "Essayez Londres, Paris, Dakar…", "جرّب لندن أو باريس أو داكار…", "Coba London, Paris, Dakar…"],
    ["Close player profile", "Cerrar perfil del jugador", "Fermer le profil du joueur", "إغلاق ملف اللاعب", "Tutup profil pemain"],
    ["Football Talent Geography", "Geografía del talento futbolístico", "Géographie du talent footballistique", "جغرافيا المواهب الكروية", "Geografi Talenta Sepak Bola"],
    ["Skip to main content", "Ir al contenido principal", "Aller au contenu principal", "انتقل إلى المحتوى الرئيسي", "Lewati ke konten utama"],
    ["Building the talent map", "Preparando el mapa de talento", "Préparation de la carte des talents", "جارٍ إعداد خريطة المواهب", "Menyiapkan peta talenta"],
    ["2025–26 snapshot", "Panorama 2025–26", "Aperçu 2025–26", "لمحة 2025–26", "Ringkasan 2025–26"],
    ["View source ↗", "Ver código ↗", "Voir le code ↗", "عرض المصدر ↗", "Lihat kode sumber ↗"],
    ["Big Five leagues · 2025–26", "Cinco grandes ligas · 2025–26", "Cinq grands championnats · 2025–26", "الدوريات الخمسة الكبرى · 2025–26", "Lima liga besar · 2025–26"],
    ["Explore where", "Descubre dónde", "Découvrez où", "اكتشف أين", "Jelajahi tempat"],
    ["players were born.", "nacieron los jugadores.", "sont nés les joueurs.", "وُلد اللاعبون.", "para pemain dilahirkan."],
    ["See the birthplace patterns behind Europe’s five leading domestic leagues, then explore individual players and clubs.", "Descubre los patrones de nacimiento en las cinco grandes ligas europeas y explora jugadores y clubes.", "Découvrez les lieux de naissance des joueurs des cinq grands championnats européens, puis explorez les joueurs et les clubs.", "اكتشف أنماط أماكن الميلاد في الدوريات الأوروبية الخمسة الكبرى، ثم استكشف اللاعبين والأندية.", "Lihat pola tempat lahir di lima liga utama Eropa, lalu jelajahi pemain dan klub."],
    ["Five leagues", "Cinco ligas", "Cinq championnats", "خمسة دوريات", "Lima liga"],
    ["About this snapshot", "Sobre estos datos", "À propos de cet aperçu", "حول هذه اللمحة", "Tentang ringkasan ini"],
    ["Includes players with at least one domestic-league appearance. Birthplace is not the same as where a player grew up or developed.", "Incluye jugadores con al menos una aparición en liga. El lugar de nacimiento no indica dónde crecieron o se formaron.", "Inclut les joueurs ayant disputé au moins un match de championnat. Le lieu de naissance ne reflète pas forcément le lieu où ils ont grandi ou été formés.", "يشمل اللاعبين الذين شاركوا مرة واحدة على الأقل في الدوري المحلي. مكان الميلاد لا يحدد مكان نشأة اللاعب أو تطوره.", "Mencakup pemain dengan setidaknya satu penampilan di liga domestik. Tempat lahir tidak selalu sama dengan tempat pemain tumbuh atau berkembang."],
    ["Read the methodology", "Leer la metodología", "Lire la méthodologie", "اقرأ المنهجية", "Baca metodologi"],
    ["League", "Liga", "Championnat", "الدوري", "Liga"],
    ["All five leagues", "Las cinco ligas", "Les cinq championnats", "جميع الدوريات الخمسة", "Kelima liga"],
    ["Club", "Club", "Club", "النادي", "Klub"],
    ["All clubs", "Todos los clubes", "Tous les clubs", "جميع الأندية", "Semua klub"],
    ["More filters", "Más filtros", "Plus de filtres", "مزيد من المرشحات", "Filter lainnya"],
    ["Age at season end", "Edad al final de la temporada", "Âge en fin de saison", "العمر في نهاية الموسم", "Usia pada akhir musim"],
    ["All ages", "Todas las edades", "Tous les âges", "جميع الأعمار", "Semua usia"],
    ["Under 21", "Menores de 21", "Moins de 21 ans", "أقل من 21", "Di bawah 21"],
    ["Birth country", "País de nacimiento", "Pays de naissance", "بلد الميلاد", "Negara kelahiran"],
    ["All birth countries", "Todos los países de nacimiento", "Tous les pays de naissance", "جميع بلدان الميلاد", "Semua negara kelahiran"],
    ["Reset filters", "Restablecer filtros", "Réinitialiser les filtres", "إعادة ضبط المرشحات", "Atur ulang filter"],
    ["Explore", "Explorar", "Explorer", "استكشف", "Jelajahi"],
    ["Compare", "Comparar", "Comparer", "قارن", "Bandingkan"],
    ["Players", "Jugadores", "Joueurs", "اللاعبون", "Pemain"],
    ["About data", "Sobre los datos", "À propos des données", "حول البيانات", "Tentang data"],
    ["Geographic distribution", "Distribución geográfica", "Répartition géographique", "التوزيع الجغرافي", "Sebaran geografis"],
    ["Talent birthplace map", "Mapa de nacimiento de jugadores", "Carte des lieux de naissance", "خريطة أماكن ميلاد اللاعبين", "Peta tempat lahir pemain"],
    ["Birthplaces", "Lugares de nacimiento", "Lieux de naissance", "أماكن الميلاد", "Tempat lahir"],
    ["Countries", "Países", "Pays", "البلدان", "Negara"],
    ["Players per 1M", "Jugadores por millón", "Joueurs par million", "لاعبون لكل مليون", "Pemain per juta"],
    ["Starts per 1M", "Titularidades por millón", "Titularisations par million", "مشاركات أساسية لكل مليون", "Starter per juta"],
    ["Map measure", "Medida del mapa", "Mesure de la carte", "مقياس الخريطة", "Ukuran peta"],
    ["Starts", "Titularidades", "Titularisations", "المشاركات الأساسية", "Starter"],
    ["starts", "titularidades", "titularisations", "مشاركات أساسية", "starter"],
    ["starters", "titulares", "titulaires", "لاعبون أساسيون", "pemain starter"],
    ["players", "jugadores", "joueurs", "لاعبين", "pemain"],
    ["sports", "deportes", "sports", "رياضات", "olahraga"],
    ["residents", "habitantes", "habitants", "نسمة", "penduduk"],
    ["people", "personas", "personnes", "أشخاص", "orang"],
    ["population", "población", "population", "السكان", "penduduk"],
    ["clubs", "clubes", "clubs", "أندية", "klub"],
    ["leagues", "ligas", "championnats", "دوريات", "liga"],
    ["places", "lugares", "lieux", "أماكن", "tempat"],
    ["countries", "países", "pays", "بلدان", "negara"],
    ["areas", "zonas", "zones", "مناطق", "wilayah"],
    ["area", "zona", "zone", "منطقة", "wilayah"],
    ["reference", "de referencia", "de référence", "مرجعية", "referensi"],
    ["players with 1+ start", "jugadores con 1+ titularidad", "joueurs avec 1 titularisation ou plus", "لاعبون بدأوا مباراة واحدة على الأقل", "pemain dengan 1+ start"],
    ["starts per 1M people", "titularidades por millón de habitantes", "titularisations par million d’habitants", "مشاركات أساسية لكل مليون نسمة", "starter per juta penduduk"],
    ["players per 1M people", "jugadores por millón de habitantes", "joueurs par million d’habitants", "لاعبون لكل مليون نسمة", "pemain per juta penduduk"],
    ["starts per 1M", "titularidades por millón", "titularisations par million", "مشاركات أساسية لكل مليون", "starter per juta"],
    ["players per 1M", "jugadores por millón", "joueurs par million", "لاعبون لكل مليون", "pemain per juta"],
    ["Players with 1+ start", "Jugadores con 1+ titularidad", "Joueurs avec 1 titularisation ou plus", "لاعبون بدأوا مباراة واحدة على الأقل", "Pemain dengan 1+ start"],
    ["Area size", "Tamaño de zona", "Taille de la zone", "حجم المنطقة", "Ukuran wilayah"],
    ["Very broad", "Muy amplia", "Très vaste", "واسعة جدًا", "Sangat luas"],
    ["Large", "Grande", "Grande", "كبيرة", "Besar"],
    ["Regional", "Regional", "Régionale", "إقليمية", "Regional"],
    ["Find a birthplace", "Buscar lugar de nacimiento", "Chercher un lieu de naissance", "ابحث عن مكان ميلاد", "Cari tempat lahir"],
    ["Clear search", "Borrar búsqueda", "Effacer la recherche", "مسح البحث", "Hapus pencarian"],
    ["Circle size =", "Tamaño del círculo =", "Taille du cercle =", "حجم الدائرة =", "Ukuran lingkaran ="],
    ["Country colour =", "Color del país =", "Couleur du pays =", "لون البلد =", "Warna negara ="],
    ["Hex colour =", "Color de la zona =", "Couleur de la zone =", "لون المنطقة =", "Warna wilayah ="],
    ["Top locations", "Principales lugares", "Principaux lieux", "أبرز الأماكن", "Lokasi teratas"],
    ["By starts", "Por titularidades", "Par titularisations", "حسب المشاركات الأساسية", "Menurut starter"],
    ["in the current selection", "en la selección actual", "dans la sélection actuelle", "في الاختيار الحالي", "dalam pilihan saat ini"],
    ["Starting XI places", "Puestos en el once inicial", "Places dans le onze de départ", "مراكز التشكيلة الأساسية", "Posisi sebelas awal"],
    ["across the season", "durante la temporada", "sur la saison", "طوال الموسم", "sepanjang musim"],
    ["Birthplace coverage", "Cobertura de lugares de nacimiento", "Couverture des lieux de naissance", "تغطية أماكن الميلاد", "Cakupan tempat lahir"],
    ["birthplace coverage", "cobertura de lugares de nacimiento", "couverture des lieux de naissance", "تغطية أماكن الميلاد", "cakupan tempat lahir"],
    ["of selected players mapped", "de los jugadores seleccionados ubicados", "des joueurs sélectionnés localisés", "من اللاعبين المختارين المحددة مواقعهم", "dari pemain terpilih yang dipetakan"],
    ["players in selection", "jugadores seleccionados", "joueurs sélectionnés", "لاعبون في الاختيار", "pemain dalam pilihan"],
    ["Leagues, clubs & generations", "Ligas, clubes y generaciones", "Championnats, clubs et générations", "الدوريات والأندية والأجيال", "Liga, klub & generasi"],
    ["Compare the competition", "Compara las ligas", "Comparer les championnats", "قارن المنافسات", "Bandingkan kompetisi"],
    ["Birthplace mix, player ages and club footprint", "Lugares de nacimiento, edades y alcance de los clubes", "Origines, âges des joueurs et empreinte des clubs", "تنوع أماكن الميلاد وأعمار اللاعبين وانتشار الأندية", "Asal kelahiran, usia pemain, dan jangkauan klub"],
    ["Club comparison", "Comparación de clubes", "Comparaison des clubs", "مقارنة الأندية", "Perbandingan klub"],
    ["Birthplace footprint", "Alcance de los lugares de nacimiento", "Empreinte des lieux de naissance", "انتشار أماكن الميلاد", "Jangkauan tempat lahir"],
    ["Starts and mapped birthplace coverage", "Titularidades y cobertura de nacimiento", "Titularisations et couverture des lieux de naissance", "المشاركات الأساسية وتغطية أماكن الميلاد", "Starter dan cakupan tempat lahir"],
    ["Age & generations", "Edad y generaciones", "Âge et générations", "العمر والأجيال", "Usia & generasi"],
    ["Who plays—and when", "Quién juega y cuándo", "Qui joue, et à quel âge", "من يلعب ومتى", "Siapa yang bermain dan kapan"],
    ["Age measured at 30 June 2026", "Edad calculada al 30 de junio de 2026", "Âge calculé au 30 juin 2026", "العمر محسوب في 30 يونيو 2026", "Usia dihitung per 30 Juni 2026"],
    ["League distribution", "Distribución por liga", "Répartition par championnat", "التوزيع حسب الدوري", "Sebaran liga"],
    ["Age distribution by league", "Distribución de edades por liga", "Répartition des âges par championnat", "توزيع الأعمار حسب الدوري", "Sebaran usia menurut liga"],
    ["Season-end age", "Edad al final de temporada", "Âge en fin de saison", "العمر بنهاية الموسم", "Usia akhir musim"],
    ["View", "Vista", "Vue", "العرض", "Tampilan"],
    ["Distribution", "Distribución", "Répartition", "التوزيع", "Sebaran"],
    ["Age distribution", "Distribución de edades", "Répartition des âges", "توزيع الأعمار", "Sebaran usia"],
    ["Age bands", "Grupos de edad", "Tranches d’âge", "الفئات العمرية", "Kelompok usia"],
    ["Leagues", "Ligas", "Championnats", "الدوريات", "Liga"],
    ["Clubs", "Clubes", "Clubs", "الأندية", "Klub"],
    ["Emerging generation", "Nueva generación", "Nouvelle génération", "الجيل الصاعد", "Generasi baru"],
    ["Youngest players", "Jugadores más jóvenes", "Joueurs les plus jeunes", "أصغر اللاعبين", "Pemain termuda"],
    ["Veteran generation", "Generación veterana", "Génération expérimentée", "الجيل المخضرم", "Generasi veteran"],
    ["Oldest players", "Jugadores de mayor edad", "Joueurs les plus âgés", "أكبر اللاعبين سنًا", "Pemain tertua"],
    ["Exact dates are used where date-of-birth validation succeeded. A “≈” symbol marks ages estimated from birth year only.", "Se usan fechas exactas cuando se verificó la fecha de nacimiento. El símbolo «≈» indica una edad estimada solo a partir del año.", "Les dates exactes sont utilisées quand la naissance a pu être vérifiée. Le symbole «≈» indique un âge estimé à partir de l’année seule.", "تُستخدم التواريخ الدقيقة عند التحقق من تاريخ الميلاد. تشير «≈» إلى عمر مقدّر من سنة الميلاد فقط.", "Tanggal pasti digunakan jika tanggal lahir telah diverifikasi. Simbol “≈” menandai usia yang diperkirakan hanya dari tahun lahir."],
    ["Player-level detail", "Detalle de jugadores", "Détail des joueurs", "تفاصيل اللاعبين", "Detail pemain"],
    ["Find a player", "Buscar un jugador", "Chercher un joueur", "ابحث عن لاعب", "Cari pemain"],
    ["Search players", "Buscar jugadores", "Chercher des joueurs", "ابحث عن لاعبين", "Cari pemain"],
    ["Players matching the current filters", "Jugadores que coinciden con los filtros", "Joueurs correspondant aux filtres", "اللاعبون المطابقون للمرشحات", "Pemain yang sesuai filter"],
    ["Player", "Jugador", "Joueur", "اللاعب", "Pemain"],
    ["Birthplace", "Lugar de nacimiento", "Lieu de naissance", "مكان الميلاد", "Tempat lahir"],
    ["Apps", "Partidos", "Matchs", "المباريات", "Penampilan"],
    ["No players found", "No se encontraron jugadores", "Aucun joueur trouvé", "لم يُعثر على لاعبين", "Tidak ada pemain"],
    ["Try another search or clear your filters.", "Prueba otra búsqueda o borra los filtros.", "Essayez une autre recherche ou effacez les filtres.", "جرّب بحثًا آخر أو امسح المرشحات.", "Coba pencarian lain atau hapus filter."],
    ["This selection has no players.", "Esta selección no tiene jugadores.", "Cette sélection ne contient aucun joueur.", "لا يوجد لاعبون في هذا الاختيار.", "Tidak ada pemain dalam pilihan ini."],
    ["Show more players", "Mostrar más jugadores", "Afficher plus de joueurs", "عرض المزيد من اللاعبين", "Tampilkan lebih banyak pemain"],
    ["Clear filters", "Borrar filtros", "Effacer les filtres", "مسح المرشحات", "Hapus filter"],
    ["No players to show", "No hay jugadores para mostrar", "Aucun joueur à afficher", "لا يوجد لاعبون للعرض", "Tidak ada pemain untuk ditampilkan"],
    ["All players shown", "Se muestran todos los jugadores", "Tous les joueurs sont affichés", "عُرض جميع اللاعبين", "Semua pemain ditampilkan"],
    ["Transparent by design", "Transparencia desde el diseño", "Transparence dès la conception", "الشفافية أساس التصميم", "Transparan sejak awal"],
    ["Coverage & methodology", "Cobertura y metodología", "Couverture et méthodologie", "التغطية والمنهجية", "Cakupan & metodologi"],
    ["No inferred or guessed birthplaces", "Sin lugares de nacimiento inferidos", "Aucun lieu de naissance supposé", "لا تُستخدم أماكن ميلاد مفترضة", "Tidak ada tempat lahir hasil perkiraan"],
    ["Birthplace resolution", "Identificación del lugar de nacimiento", "Identification des lieux de naissance", "تحديد أماكن الميلاد", "Penentuan tempat lahir"],
    ["Name-and-birth-year matched players with geographic coordinates.", "Jugadores identificados por nombre y año de nacimiento con coordenadas geográficas.", "Joueurs associés par nom et année de naissance à des coordonnées géographiques.", "لاعبون طابقت أسماؤهم وسنوات ميلادهم إحداثيات جغرافية.", "Pemain yang dicocokkan berdasarkan nama dan tahun lahir dengan koordinat geografis."],
    ["mapped", "ubicados", "localisés", "محددو الموقع", "dipetakan"],
    ["unresolved", "sin resolver", "non résolus", "دون تحديد", "belum teridentifikasi"],
    ["mapped starts", "titularidades ubicadas", "titularisations localisées", "مشاركات أساسية محددة الموقع", "starter yang dipetakan"],
    ["total", "total", "total", "الإجمالي", "total"],
    ["Contribution coverage", "Cobertura de contribuciones", "Couverture des contributions", "تغطية المشاركات", "Cakupan kontribusi"],
    ["Recorded starts connected to a validated birthplace.", "Titularidades registradas vinculadas a un lugar de nacimiento verificado.", "Titularisations enregistrées liées à un lieu de naissance vérifié.", "المشاركات الأساسية المسجلة المرتبطة بمكان ميلاد موثّق.", "Starter tercatat yang terkait dengan tempat lahir terverifikasi."],
    ["Resolution method", "Método de identificación", "Méthode d’identification", "طريقة التحديد", "Metode penentuan"],
    ["Identity first.", "Primero la identidad.", "L’identité d’abord.", "الهوية أولًا.", "Identitas lebih dulu."],
    ["Geography second.", "Luego la geografía.", "La géographie ensuite.", "ثم الجغرافيا.", "Geografi kemudian."],
    ["Match an exact label or Wikipedia title redirect.", "Buscar una coincidencia exacta o redirección de Wikipedia.", "Associer un nom exact ou une redirection de titre Wikipédia.", "مطابقة الاسم بدقة أو إعادة توجيه عنوان ويكيبيديا.", "Cocokkan nama persis atau pengalihan judul Wikipedia."],
    ["Require the player’s source birth year.", "Exigir el año de nacimiento de la fuente.", "Exiger l’année de naissance fournie par la source.", "اشتراط سنة ميلاد اللاعب من المصدر.", "Wajibkan tahun lahir pemain dari sumber."],
    ["Resolve the birthplace entity and coordinates.", "Identificar la entidad del lugar de nacimiento y sus coordenadas.", "Identifier le lieu de naissance et ses coordonnées.", "تحديد كيان مكان الميلاد وإحداثياته.", "Tentukan entitas tempat lahir dan koordinatnya."],
    ["Queue every ambiguous match for manual QA.", "Enviar las coincidencias ambiguas a revisión manual.", "Soumettre les correspondances ambiguës à une vérification manuelle.", "إحالة كل مطابقة ملتبسة إلى المراجعة اليدوية.", "Masukkan setiap kecocokan ambigu ke pemeriksaan manual."],
    ["Manual QA queue", "Pendientes de revisión manual", "Vérifications manuelles en attente", "قائمة المراجعة اليدوية", "Antrean pemeriksaan manual"],
    ["Unresolved players", "Jugadores sin resolver", "Joueurs non résolus", "لاعبون دون تحديد", "Pemain belum teridentifikasi"],
    ["name birth year not found", "nombre y año de nacimiento no encontrados", "nom et année de naissance introuvables", "لم يُعثر على الاسم وسنة الميلاد", "nama dan tahun lahir tidak ditemukan"],
    ["birthplace missing", "falta el lugar de nacimiento", "lieu de naissance manquant", "مكان الميلاد مفقود", "tempat lahir tidak tersedia"],
    ["ambiguous name birth year", "nombre y año de nacimiento ambiguos", "nom et année de naissance ambigus", "الاسم وسنة الميلاد ملتبسان", "nama dan tahun lahir ambigu"],
    ["birth year missing", "falta el año de nacimiento", "année de naissance manquante", "سنة الميلاد مفقودة", "tahun lahir tidak tersedia"],
    ["Source & licence", "Fuentes y licencia", "Sources et licence", "المصادر والترخيص", "Sumber & lisensi"],
    ["Reproducible and attributed.", "Reproducible y con atribución.", "Reproductible et sourcé.", "قابل لإعادة الإنتاج مع توثيق المصادر.", "Dapat direproduksi dan menyebut sumber."],
    ["Appearance statistics come from the MIT-licensed Football Players Stats dataset, derived from FBref. Birthplaces come from Wikidata; local population totals come from WorldPop.", "Las estadísticas proceden de Football Players Stats (licencia MIT), basado en FBref. Los lugares de nacimiento proceden de Wikidata y la población local de WorldPop.", "Les statistiques viennent du jeu de données Football Players Stats sous licence MIT, dérivé de FBref. Les lieux de naissance viennent de Wikidata et les populations locales de WorldPop.", "تأتي إحصاءات المشاركات من مجموعة Football Players Stats المرخّصة وفق MIT والمشتقة من FBref. أما أماكن الميلاد فمن Wikidata والسكان المحليون من WorldPop.", "Statistik penampilan berasal dari dataset Football Players Stats berlisensi MIT, turunan FBref. Tempat lahir berasal dari Wikidata; jumlah penduduk lokal dari WorldPop."],
    ["Stats dataset", "Datos estadísticos", "Données statistiques", "بيانات الإحصاءات", "Dataset statistik"],
    ["Starts QA", "Control de titularidades", "Contrôle des titularisations", "تدقيق المشاركات الأساسية", "Pemeriksaan starter"],
    ["Full coverage notes →", "Notas completas de cobertura →", "Notes complètes sur la couverture →", "تفاصيل التغطية الكاملة ←", "Catatan cakupan lengkap →"],
    ["Built as a reproducible research project. Data scope matters.", "Creado como proyecto de investigación reproducible. El alcance de los datos importa.", "Conçu comme un projet de recherche reproductible. Le périmètre des données compte.", "بُني كمشروع بحثي قابل لإعادة الإنتاج. نطاق البيانات مهم.", "Dibangun sebagai proyek riset yang dapat direproduksi. Cakupan data itu penting."],
    ["2025–26 stats: hubertsidorowicz dataset · Birthplaces: Wikidata", "Estadísticas 2025–26: datos de hubertsidorowicz · Nacimientos: Wikidata", "Stats 2025–26 : données hubertsidorowicz · Naissances : Wikidata", "إحصاءات 2025–26: بيانات hubertsidorowicz · أماكن الميلاد: Wikidata", "Statistik 2025–26: dataset hubertsidorowicz · Tempat lahir: Wikidata"],
    ["Player profile", "Perfil del jugador", "Profil du joueur", "ملف اللاعب", "Profil pemain"],
    ["Minutes", "Minutos", "Minutes", "الدقائق", "Menit"],
    ["Goals", "Goles", "Buts", "الأهداف", "Gol"],
    ["Assists", "Asistencias", "Passes décisives", "التمريرات الحاسمة", "Assist"],
    ["Place of birth", "Lugar de nacimiento", "Lieu de naissance", "مكان الميلاد", "Tempat lahir"],
    ["Born", "Nacido", "Né", "وُلد", "Lahir"],
    ["Map unavailable until this birthplace clears QA.", "Mapa no disponible hasta que se verifique este lugar de nacimiento.", "Carte indisponible tant que ce lieu de naissance n’est pas vérifié.", "الخريطة غير متاحة حتى يُراجَع مكان الميلاد هذا.", "Peta tidak tersedia sampai tempat lahir ini lolos pemeriksaan."],
    ["Sports", "Deportes", "Sports", "الرياضات", "Olahraga"],
    ["All sports", "Todos los deportes", "Tous les sports", "جميع الرياضات", "Semua olahraga"],
    ["Compare sports", "Comparar deportes", "Comparer les sports", "قارن الرياضات", "Bandingkan olahraga"],
    ["Choose an edition", "Elige una edición", "Choisissez une édition", "اختر نسخة", "Pilih edisi"],
    ["Team sports", "Deportes de equipo", "Sports collectifs", "رياضات جماعية", "Olahraga beregu"],
    ["Individual & racing", "Individuales y motor", "Individuels et courses", "فردية وسباقات", "Individual & balap"],
    ["Browse editions", "Ver ediciones", "Parcourir les éditions", "تصفح النسخ", "Jelajahi edisi"],
    ["Source ↗", "Código ↗", "Source ↗", "المصدر ↗", "Sumber ↗"],
    ["Sport", "Deporte", "Sport", "الرياضة", "Olahraga"],
    ["Compare sport", "Comparar deporte", "Comparer un sport", "قارن الرياضة", "Bandingkan olahraga"],
    ["Same place, another sport.", "El mismo lugar, otro deporte.", "Même lieu, autre sport.", "المكان نفسه، رياضة أخرى.", "Tempat sama, olahraga berbeda."],
    ["Viewpoint and map mode carry over; each sport keeps its own workload unit.", "La vista y el modo del mapa se conservan; cada deporte mantiene su propia unidad.", "La vue et le mode de carte sont conservés ; chaque sport garde sa propre unité de mesure.", "يُحافَظ على زاوية العرض ووضع الخريطة؛ ولكل رياضة وحدة قياسها.", "Sudut pandang dan mode peta tetap sama; tiap olahraga memakai satuannya sendiri."],
    ["Compare side by side →", "Comparar en paralelo →", "Comparer côte à côte →", "قارن جنبًا إلى جنب ←", "Bandingkan berdampingan →"],
    ["Loading population data…", "Cargando datos de población…", "Chargement des données de population…", "جارٍ تحميل بيانات السكان…", "Memuat data penduduk…"],
    ["Preparing the population view…", "Preparando la vista de población…", "Préparation de la vue par population…", "جارٍ إعداد عرض السكان…", "Menyiapkan tampilan penduduk…"],
    ["Population estimate unavailable", "Estimación de población no disponible", "Estimation de population indisponible", "تقدير السكان غير متاح", "Perkiraan penduduk tidak tersedia"],
    ["Population unavailable", "Población no disponible", "Population indisponible", "بيانات السكان غير متاحة", "Data penduduk tidak tersedia"],
    ["Populated land", "Zona poblada", "Terre habitée", "أرض مأهولة", "Wilayah berpenduduk"],
    ["Small-sample cell", "Zona con muestra pequeña", "Zone à petit échantillon", "منطقة بعينة صغيرة", "Wilayah dengan sampel kecil"],
    ["unavailable", "no disponible", "indisponible", "غير متاح", "tidak tersedia"],
    ["No mapped players", "Sin jugadores ubicados", "Aucun joueur localisé", "لا يوجد لاعبون محددو الموقع", "Tidak ada pemain yang dipetakan"],
    ["No mapped players in this selection", "Sin jugadores ubicados en esta selección", "Aucun joueur localisé dans cette sélection", "لا يوجد لاعبون محددو الموقع في هذا الاختيار", "Tidak ada pemain yang dipetakan dalam pilihan ini"],
    ["Unclassified", "Sin clasificar", "Non classé", "غير مصنف", "Belum diklasifikasikan"],
    ["Africa", "África", "Afrique", "أفريقيا", "Afrika"],
    ["Asia", "Asia", "Asie", "آسيا", "Asia"],
    ["Europe", "Europa", "Europe", "أوروبا", "Eropa"],
    ["North America", "América del Norte", "Amérique du Nord", "أمريكا الشمالية", "Amerika Utara"],
    ["South America", "América del Sur", "Amérique du Sud", "أمريكا الجنوبية", "Amerika Selatan"],
    ["Oceania", "Oceanía", "Océanie", "أوقيانوسيا", "Oseania"],
    ["Antarctica", "Antártida", "Antarctique", "القارة القطبية الجنوبية", "Antarktika"],
    ["Kingdom of Denmark", "Reino de Dinamarca", "Royaume du Danemark", "مملكة الدنمارك", "Kerajaan Denmark"],
    ["Kingdom of the Netherlands", "Reino de los Países Bajos", "Royaume des Pays-Bas", "مملكة هولندا", "Kerajaan Belanda"],
    ["Current dashboard selection", "Selección actual del panel", "Sélection actuelle du tableau de bord", "الاختيار الحالي للوحة", "Pilihan dasbor saat ini"],
    ["WorldPop 2025 · 1 km grid", "WorldPop 2025 · cuadrícula de 1 km", "WorldPop 2025 · grille de 1 km", "WorldPop 2025 · شبكة 1 كم", "WorldPop 2025 · grid 1 km"],
    ["Interpret carefully: fewer than two players, fewer than 100,000 residents, or no population estimate.", "Interpreta con cautela: menos de dos jugadores, menos de 100.000 habitantes o sin estimación de población.", "À interpréter avec prudence : moins de deux joueurs, moins de 100 000 habitants ou aucune estimation de population.", "فسّر بحذر: أقل من لاعبين اثنين أو 100,000 نسمة أو لا يوجد تقدير للسكان.", "Tafsirkan dengan hati-hati: kurang dari dua pemain, kurang dari 100.000 penduduk, atau tanpa perkiraan penduduk."],
    ["No birthplaces match this selection.", "Ningún lugar de nacimiento coincide con esta selección.", "Aucun lieu de naissance ne correspond à cette sélection.", "لا توجد أماكن ميلاد مطابقة لهذا الاختيار.", "Tidak ada tempat lahir yang sesuai dengan pilihan ini."],
    ["No countries match this selection.", "Ningún país coincide con esta selección.", "Aucun pays ne correspond à cette sélection.", "لا توجد بلدان مطابقة لهذا الاختيار.", "Tidak ada negara yang sesuai dengan pilihan ini."],
    ["No reliable local areas match this selection.", "Ninguna zona local fiable coincide con esta selección.", "Aucune zone locale fiable ne correspond à cette sélection.", "لا توجد مناطق محلية موثوقة مطابقة لهذا الاختيار.", "Tidak ada wilayah lokal yang andal sesuai pilihan ini."],
    ["Birth-country comparison unavailable", "Comparación de países de nacimiento no disponible", "Comparaison des pays de naissance indisponible", "مقارنة بلدان الميلاد غير متاحة", "Perbandingan negara kelahiran tidak tersedia"],
    ["Country reference data could not be loaded. Club and age comparisons are still available below.", "No se pudieron cargar los países de referencia. Las comparaciones de clubes y edades siguen disponibles.", "Les données de référence des pays n’ont pas pu être chargées. Les comparaisons des clubs et des âges restent disponibles.", "تعذر تحميل بيانات البلدان المرجعية. ما زالت مقارنات الأندية والأعمار متاحة أدناه.", "Data referensi negara gagal dimuat. Perbandingan klub dan usia masih tersedia."],
    ["diversity", "diversidad", "diversité", "التنوع", "keragaman"],
    ["/100 diversity", "/100 diversidad", "/100 diversité", "/100 تنوع", "/100 keragaman"],
    ["domestic-born", "nacidos en el país", "nés dans le pays", "مولودون محليًا", "lahir di negara asal"],
    ["birth countries", "países de nacimiento", "pays de naissance", "بلدان الميلاد", "negara kelahiran"],
    ["continents", "continentes", "continents", "قارات", "benua"],
    ["median age", "edad mediana", "âge médian", "العمر الوسيط", "median usia"],
    ["Leading birth countries", "Principales países de nacimiento", "Principaux pays de naissance", "أبرز بلدان الميلاد", "Negara kelahiran teratas"],
    ["No league comparison matches this selection.", "Ninguna liga coincide con esta selección.", "Aucun championnat ne correspond à cette sélection.", "لا توجد مقارنة دوريات مطابقة لهذا الاختيار.", "Tidak ada perbandingan liga yang sesuai pilihan ini."],
    ["No age data matches this selection.", "No hay datos de edad para esta selección.", "Aucune donnée d’âge pour cette sélection.", "لا توجد بيانات عمر مطابقة لهذا الاختيار.", "Tidak ada data usia yang sesuai pilihan ini."],
    ["Median age", "Edad mediana", "Âge médian", "العمر الوسيط", "Median usia"],
    ["at 30 June 2026", "al 30 de junio de 2026", "au 30 juin 2026", "في 30 يونيو 2026", "per 30 Juni 2026"],
    ["Age 30+", "Edad 30+", "Âge 30+", "العمر 30+", "Usia 30+"],
    ["Exact ages", "Edades exactas", "Âges exacts", "أعمار دقيقة", "Usia pasti"],
    ["of players", "de jugadores", "des joueurs", "من اللاعبين", "dari pemain"],
    ["remaining values approximate", "los demás valores son aproximados", "autres valeurs approximatives", "القيم الأخرى تقريبية", "nilai lainnya perkiraan"],
    ["Smoothed age distribution · curves share one scale", "Distribución de edades suavizada · las curvas comparten escala", "Répartition des âges lissée · même échelle pour les courbes", "توزيع أعمار ممهد · جميع المنحنيات بمقياس واحد", "Sebaran usia diperhalus · kurva memakai skala yang sama"],
    ["Each row totals 100% of players with an available age", "Cada fila suma el 100 % de los jugadores con edad disponible", "Chaque ligne représente 100 % des joueurs dont l’âge est connu", "يمثل كل صف 100% من اللاعبين الذين تتوفر أعمارهم", "Tiap baris berjumlah 100% pemain dengan usia tersedia"],
    ["youngest median first", "menor edad mediana primero", "âge médian le plus jeune d’abord", "الوسيط الأصغر أولًا", "median termuda lebih dulu"],
    ["No clubs match this selection.", "Ningún club coincide con esta selección.", "Aucun club ne correspond à cette sélection.", "لا توجد أندية مطابقة لهذا الاختيار.", "Tidak ada klub yang sesuai pilihan ini."],
    ["DOB unavailable", "Fecha de nacimiento no disponible", "Date de naissance indisponible", "تاريخ الميلاد غير متاح", "Tanggal lahir tidak tersedia"],
    ["Unavailable", "No disponible", "Indisponible", "غير متاح", "Tidak tersedia"],
    ["Position unavailable", "Posición no disponible", "Poste indisponible", "المركز غير متاح", "Posisi tidak tersedia"],
    ["Nationality unavailable", "Nacionalidad no disponible", "Nationalité indisponible", "الجنسية غير متاحة", "Kewarganegaraan tidak tersedia"],
    ["Birthplace awaiting QA", "Lugar de nacimiento pendiente de revisión", "Lieu de naissance en attente de vérification", "مكان الميلاد قيد المراجعة", "Tempat lahir menunggu pemeriksaan"],
    ["Age unavailable", "Edad no disponible", "Âge indisponible", "العمر غير متاح", "Usia tidak tersedia"],
    ["No active filters", "No hay filtros activos", "Aucun filtre actif", "لا توجد مرشحات نشطة", "Tidak ada filter aktif"],
    ["11 × matches ✓", "11 × partidos ✓", "11 × matchs ✓", "11 × مباريات ✓", "11 × pertandingan ✓"],
    ["median", "mediana", "médiane", "الوسيط", "median"],
    ["ago", "hace", "il y a", "منذ", "lalu"],
    ["Updated", "Actualizado", "Mis à jour", "حُدّث", "Diperbarui"],
    ["Dataset generated", "Datos generados", "Données générées", "أُنتجت البيانات", "Dataset dibuat"],
    ["filter", "filtro", "filtre", "مرشح", "filter"],
    ["filters", "filtros", "filtres", "مرشحات", "filter"],
    ["active", "activos", "actifs", "نشطة", "aktif"],
    ["The population view is unavailable right now. Birthplace and country views still work.", "La vista de población no está disponible ahora. Las vistas de lugares de nacimiento y países siguen funcionando.", "La vue par population est momentanément indisponible. Les vues par lieu de naissance et pays restent disponibles.", "عرض السكان غير متاح حاليًا. ما زال عرضا أماكن الميلاد والبلدان يعملان.", "Tampilan penduduk saat ini tidak tersedia. Tampilan tempat lahir dan negara masih berfungsi."],
    ["Country boundaries could not be loaded. The rest of the dashboard is available.", "No se pudieron cargar los límites de los países. El resto del panel está disponible.", "Les frontières des pays n’ont pas pu être chargées. Le reste du tableau de bord est disponible.", "تعذر تحميل حدود البلدان. بقية اللوحة متاحة.", "Batas negara gagal dimuat. Bagian dasbor lainnya tetap tersedia."],
    ["The dashboard data could not be loaded. Please refresh or try again shortly.", "No se pudieron cargar los datos. Actualiza la página o vuelve a intentarlo pronto.", "Les données n’ont pas pu être chargées. Actualisez la page ou réessayez dans un instant.", "تعذر تحميل بيانات اللوحة. حدّث الصفحة أو حاول مجددًا بعد قليل.", "Data dasbor gagal dimuat. Muat ulang halaman atau coba lagi sebentar lagi."],
  ];

  const codes = ["en", "es", "fr", "ar", "id"];
  const locales = { en: "en-US", es: "es-ES", fr: "fr-FR", ar: "ar-u-nu-latn", id: "id-ID" };
  const dictionary = new Map(rows.map((row) => [row[0], row]));
  const countryCodes = new Map([
    ["Ivory Coast", "CI"], ["Czech Republic", "CZ"],
    ["Turkey", "TR"], ["The Gambia", "GM"], ["Democratic Republic of the Congo", "CD"],
    ["Bosnia and Herzegovina", "BA"], ["Republic of the Congo", "CG"],
  ]);
  const displayNames = new Map();
  if (Intl.DisplayNames) {
    const englishNames = new Intl.DisplayNames(["en"], { type: "region" });
    for (let first = 65; first <= 90; first += 1) {
      for (let second = 65; second <= 90; second += 1) {
        const code = String.fromCharCode(first, second);
        const name = englishNames.of(code);
        if (name !== code) countryCodes.set(name, code);
      }
    }
  }
  const textRecords = new WeakMap();
  const attributeRecords = new WeakMap();
  const attributes = ["aria-label", "title", "placeholder", "data-label"];
  let language = "en";
  try {
    const saved = localStorage.getItem("football-geo-language");
    if (codes.includes(saved)) language = saved;
  } catch (_) { /* Storage can be disabled. */ }

  function word(source) {
    return dictionary.get(source)?.[codes.indexOf(language)] || source;
  }

  function translateCore(source) {
    if (language === "en") return source;
    if (dictionary.has(source)) return word(source);
    if (countryCodes.has(source) && Intl.DisplayNames) {
      if (!displayNames.has(language)) displayNames.set(language, new Intl.DisplayNames([locales[language]], { type: "region" }));
      return displayNames.get(language).of(countryCodes.get(source));
    }
    let match;
    if ((match = source.match(/^Explore (\d+) sports$/))) return `${word("Explore")} ${match[1]} ${word("sports")}`;
    if ((match = source.match(/^([\d.,\s]+) active (filter|filters)$/))) return `${match[1]} ${word("filters")} ${word("active")}`;
    if ((match = source.match(/^All (\d+) clubs$/))) return ({es:`Todos los ${match[1]} clubes`,fr:`Les ${match[1]} clubs`,ar:`جميع الأندية الـ${match[1]}`,id:`Semua ${match[1]} klub`})[language];
    if ((match = source.match(/^([\d.,\s—]+) (players|clubs|leagues|places|countries|areas|starts|mapped starts|mapped|unresolved|total|residents|starters)$/))) {
      return `${match[1]} ${word(match[2])}`;
    }
    if ((match = source.match(/^\+([\d.,\s]+) more players$/))) return `+${match[1]} ${word("players")}`;
    if ((match = source.match(/^([\d.,\s]+) players in (this|the current) selection$/))) return `${match[1]} ${word("players")} ${word("in the current selection")}`;
    if ((match = source.match(/^([\d.,\s]+) (mapped players|reference areas)$/))) return `${match[1]} ${match[2] === "mapped players" ? `${word("players")} ${word("mapped")}` : `${word("areas")} ${word("reference")}`}`;
    if ((match = source.match(/^([\d.,\s]+) players with 1\+ start$/))) return `${match[1]} ${word("players with 1+ start")}`;
    if ((match = source.match(/^([\d.,\s]+) players · (.+) highlighted$/))) return `${match[1]} ${word("players")} · ${translateCore(match[2])}`;
    if ((match = source.match(/^([\d.,\s]+) of ([\d.,\s]+) players mapped$/))) return `${match[1]} / ${match[2]} ${word("players")} ${word("mapped")}`;
    if ((match = source.match(/^([\d.,\s]+)% (of players|birthplace coverage)$/))) return `${match[1]}% ${word(match[2])}`;
    if ((match = source.match(/^([\d.,\s]+) players, ([\d.,\s]+(?:\.\d+)?)%$/))) return `${match[1]} ${word("players")}, ${match[2]}%`;
    if ((match = source.match(/^(.+) population areas are unavailable\. Try another size\.$/))) return `${translateCore(match[1])} ${{es:"zonas de población no disponibles. Prueba otro tamaño.",fr:"zones de population indisponibles. Essayez une autre taille.",ar:"مناطق سكانية غير متاحة. جرّب حجمًا آخر.",id:"wilayah penduduk tidak tersedia. Coba ukuran lain."}[language]}`;
    if ((match = source.match(/^By (.+)$/))) return `${{es:"Por",fr:"Par",ar:"حسب",id:"Menurut"}[language]} ${translateCore(match[1])}`;
    if ((match = source.match(/^Countries by (.+)$/))) return `${word("Countries")} · ${translateCore(`By ${match[1]}`)}`;
    if ((match = source.match(/^(League|Club) distribution$/))) return `${word("Distribution")} · ${word(match[1])}`;
    if ((match = source.match(/^(Age distribution|Age bands) by (league|club)$/))) return `${word(match[1])} · ${word(match[2] === "league" ? "League" : "Club")}`;
    if ((match = source.match(/^Age distribution for (.+)$/))) return `${word("Age distribution")} · ${match[1]}`;
    if ((match = source.match(/^(.+) age bands\. (.+)$/))) return `${match[1]} · ${word("Age bands")}. ${translateCore(match[2])}`;
    if ((match = source.match(/^(.+) · ([\d.,\s]+) players · median (.+)$/))) return `${match[1]} · ${match[2]} ${word("players")} · ${word("median")} ${match[3]}`;
    if ((match = source.match(/^Born in:? (.+)$/))) return `${{es:"Nacido en",fr:"Né en",ar:"وُلد في",id:"Lahir di"}[language]}: ${translateCore(match[1])}`;
    if ((match = source.match(/^(.+), (.+)$/)) && (countryCodes.has(match[2]) || dictionary.has(match[2]))) return `${match[1]}, ${translateCore(match[2])}`;
    if ((match = source.match(/^(League|Club|Age): (.+)$/))) return `${word(match[1])}: ${translateCore(match[2])}`;
    if ((match = source.match(/^([\d.,\s]+) active · ([\d.,\s]+) reference$/))) return `${match[1]} ${{es:"activas",fr:"actives",ar:"نشطة",id:"aktif"}[language]} · ${match[2]} ${{es:"de referencia",fr:"de référence",ar:"مرجعية",id:"referensi"}[language]}`;
    if ((match = source.match(/^([\d.,\s]+) (very broad|large|regional) areas$/i))) return `${match[1]} ${word(match[2][0].toUpperCase() + match[2].slice(1))} ${word("areas")}`;
    if ((match = source.match(/^Showing (.+) of (.+) players in this selection$/))) return `${{es:"Mostrando",fr:"Affichage de",ar:"عرض",id:"Menampilkan"}[language]} ${match[1]} / ${match[2]} ${word("players")}`;
    if ((match = source.match(/^Show (\d+) more(?: players)?$/))) return `${{es:"Mostrar",fr:"Afficher",ar:"عرض",id:"Tampilkan"}[language]} ${match[1]} ${word("players")}`;
    if ((match = source.match(/^([\d.,\s]+) years at season end$/))) return `${match[1]} ${{es:"años al final de temporada",fr:"ans en fin de saison",ar:"سنة بنهاية الموسم",id:"tahun pada akhir musim"}[language]}`;
    if ((match = source.match(/^([\d.,\s]+) (active|reference)$/))) return `${match[1]} ${word(match[2])}`;
    if ((match = source.match(/^2025–26 · Updated (.+)$/))) return `2025–26 · ${word("Updated")} ${match[1]}`;
    if ((match = source.match(/^Dataset generated (.+)$/))) return `${word("Dataset generated")} ${match[1]}`;
    if ((match = source.match(/^(.+) per 1M(?: people)?$/))) return `${translateCore(match[1])} ${{es:"por millón de personas",fr:"par million de personnes",ar:"لكل مليون نسمة",id:"per juta orang"}[language]}`;
    if ((match = source.match(/^population (.+)$/))) return `${word("population")} ${translateCore(match[1])}`;
    if ((match = source.match(/^([\d.,\s]+) players · ([\d.,\s]+) starts$/))) return `${match[1]} ${word("players")} · ${match[2]} ${word("starts")}`;
    if ((match = source.match(/^(Zoom to|Open profile for|Remove) (.+)$/))) return `${{"Zoom to":{es:"Acercar a",fr:"Zoomer sur",ar:"تكبير إلى",id:"Perbesar ke"},"Open profile for":{es:"Abrir perfil de",fr:"Ouvrir le profil de",ar:"افتح ملف",id:"Buka profil"},Remove:{es:"Quitar",fr:"Retirer",ar:"إزالة",id:"Hapus"}}[match[1]][language]} ${translateCore(match[2])}`;
    if ((match = source.match(/^(.+?) (reference area|area)$/))) {
      const name = translateCore(match[1]);
      if (match[2] === "reference area") return ({es:`Zona de referencia: ${name}`,fr:`Zone de référence : ${name}`,ar:`منطقة مرجعية: ${name}`,id:`Wilayah referensi: ${name}`})[language];
      return ({es:`Zona de ${name}`,fr:`Zone de ${name}`,ar:`منطقة ${name}`,id:`Wilayah ${name}`})[language];
    }
    if ((match = source.match(/^(.+) · (.+)$/))) return `${translateCore(match[1])} · ${translateCore(match[2])}`;
    return source;
  }

  function translate(source) {
    const match = String(source).match(/^(\s*)([\s\S]*?)(\s*)$/);
    return match[1] + translateCore(match[2]) + match[3];
  }

  function renderText(node) {
    if (node.parentElement?.closest("script, style, noscript, #site-language")) return;
    const previous = textRecords.get(node);
    const source = previous && node.nodeValue === previous.rendered ? previous.source : node.nodeValue;
    const rendered = translate(source);
    textRecords.set(node, { source, rendered });
    if (node.nodeValue !== rendered) node.nodeValue = rendered;
  }

  function renderAttributes(element) {
    const remembered = attributeRecords.get(element) || {};
    for (const name of attributes) {
      if (!element.hasAttribute(name)) continue;
      const current = element.getAttribute(name);
      const previous = remembered[name];
      const source = previous && current === previous.rendered ? previous.source : current;
      const rendered = translate(source);
      remembered[name] = { source, rendered };
      if (current !== rendered) element.setAttribute(name, rendered);
    }
    attributeRecords.set(element, remembered);
  }

  function renderSubtree(root) {
    if (root.nodeType === Node.TEXT_NODE) { renderText(root); return; }
    if (root.nodeType !== Node.ELEMENT_NODE) return;
    renderAttributes(root);
    for (const element of root.querySelectorAll("*")) renderAttributes(element);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) renderText(walker.currentNode);
  }

  function applyLanguage() {
    document.documentElement.lang = language;
    document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
    const title = dictionary.get("Football Talent Geography")?.[codes.indexOf(language)];
    if (title) document.title = title;
    const select = document.querySelector("#site-language");
    if (select) select.value = language;
    renderSubtree(document.body);
  }

  function setLanguage(next) {
    if (!codes.includes(next)) return;
    language = next;
    try { localStorage.setItem("football-geo-language", language); } catch (_) { /* Storage can be disabled. */ }
    applyLanguage();
    document.dispatchEvent(new CustomEvent("footballlanguagechange", { detail: { language } }));
  }

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === "characterData") renderText(mutation.target);
      else if (mutation.type === "attributes") renderAttributes(mutation.target);
      else for (const node of mutation.addedNodes) renderSubtree(node);
    }
  });

  window.FootballLanguage = { get language() { return language; }, get locale() { return locales[language]; }, setLanguage, translate };
  applyLanguage();
  document.querySelector("#site-language")?.addEventListener("change", (event) => setLanguage(event.target.value));
  observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: attributes });
})();
