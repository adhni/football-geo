(function () {
  "use strict";

  // English is the source text in the static pages and dashboard renderers.
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

  rows.push(...[
    ["Talent Geography", "Geografía del talento", "Géographie du talent", "جغرافيا المواهب", "Geografi Talenta"],
    ["Football", "Fútbol", "Football", "كرة القدم", "Sepak bola"],
    ["Cricket", "Críquet", "Cricket", "الكريكيت", "Kriket"],
    ["Volleyball", "Voleibol", "Volley-ball", "الكرة الطائرة", "Bola voli"],
    ["Athletics", "Atletismo", "Athlétisme", "ألعاب القوى", "Atletik"],
    ["Tennis", "Tenis", "Tennis", "التنس", "Tenis"],
    ["Padel", "Pádel", "Padel", "البادل", "Padel"],
    ["Badminton", "Bádminton", "Badminton", "الريشة الطائرة", "Bulu tangkis"],
    ["Golf", "Golf", "Golf", "الغولف", "Golf"],
    ["Basketball", "Baloncesto", "Basket-ball", "كرة السلة", "Bola basket"],
    ["Formula", "Fórmula", "Formule", "الفورمولا", "Formula"],
    ["AFL", "AFL", "AFL", "الدوري الأسترالي", "AFL"],
    ["NRL", "NRL", "NRL", "دوري الرغبي الأسترالي", "NRL"],
    ["NBA", "NBA", "NBA", "الدوري الأمريكي لكرة السلة", "NBA"],
    ["NFL", "NFL", "NFL", "الدوري الأمريكي لكرة القدم", "NFL"],
    ["NHL", "NHL", "NHL", "دوري الهوكي الأمريكي", "NHL"],
    ["MLB", "MLB", "MLB", "دوري البيسبول الأمريكي", "MLB"],
    ["UFC", "UFC", "UFC", "يو إف سي", "UFC"],
    ["MotoGP", "MotoGP", "MotoGP", "موتو جي بي", "MotoGP"],
    ["Driver", "Piloto", "Pilote", "السائق", "Pembalap"],
    ["Drivers", "Pilotos", "Pilotes", "السائقون", "Pembalap"],
    ["drivers", "pilotos", "pilotes", "سائقين", "pembalap"],
    ["Rider", "Piloto", "Pilote", "المتسابق", "Pembalap"],
    ["Riders", "Pilotos", "Pilotes", "المتسابقون", "Pembalap"],
    ["riders", "pilotos", "pilotes", "متسابقين", "pembalap"],
    ["Fighter", "Luchador", "Combattant", "المقاتل", "Petarung"],
    ["Fighters", "Luchadores", "Combattants", "المقاتلون", "Petarung"],
    ["fighters", "luchadores", "combattants", "مقاتلين", "petarung"],
    ["Athlete", "Atleta", "Athlète", "الرياضي", "Atlet"],
    ["Athletes", "Atletas", "Athlètes", "الرياضيون", "Atlet"],
    ["athletes", "atletas", "athlètes", "رياضيين", "atlet"],
    ["Golfer", "Golfista", "Golfeur", "لاعب الغولف", "Pegolf"],
    ["Golfers", "Golfistas", "Golfeurs", "لاعبو الغولف", "Pegolf"],
    ["golfers", "golfistas", "golfeurs", "لاعبي الغولف", "pegolf"],
    ["Cricketers", "Jugadores de críquet", "Joueurs de cricket", "لاعبو الكريكيت", "Pemain kriket"],
    ["cricketers", "jugadores de críquet", "joueurs de cricket", "لاعبي الكريكيت", "pemain kriket"],
    ["Teams", "Equipos", "Équipes", "الفرق", "Tim"],
    ["Team", "Equipo", "Équipe", "الفريق", "Tim"],
    ["teams", "equipos", "équipes", "فرق", "tim"],
    ["team", "equipo", "équipe", "فريق", "tim"],
    ["National team", "Selección nacional", "Équipe nationale", "المنتخب الوطني", "Tim nasional"],
    ["national teams", "selecciones nacionales", "équipes nationales", "منتخبات وطنية", "tim nasional"],
    ["Division", "División", "Division", "الفئة", "Divisi"],
    ["Divisions", "Divisiones", "Divisions", "الفئات", "Divisi"],
    ["divisions", "divisiones", "divisions", "فئات", "divisi"],
    ["Conference", "Conferencia", "Conférence", "المجموعة", "Konferensi"],
    ["Conferences", "Conferencias", "Conférences", "المجموعات", "Konferensi"],
    ["Series", "Categoría", "Série", "الفئة", "Seri"],
    ["Tour", "Circuito", "Circuit", "الجولة", "Tur"],
    ["Gender", "Género", "Genre", "الجنس", "Gender"],
    ["Events", "Pruebas", "Épreuves", "الفعاليات", "Nomor"],
    ["Event", "Prueba", "Épreuve", "الفعالية", "Nomor"],
    ["Matches", "Partidos", "Matchs", "المباريات", "Pertandingan"],
    ["matches", "partidos", "matchs", "مباريات", "pertandingan"],
    ["Games", "Partidos", "Matchs", "المباريات", "Pertandingan"],
    ["games", "partidos", "matchs", "مباريات", "pertandingan"],
    ["Appearances", "Participaciones", "Apparitions", "المشاركات", "Penampilan"],
    ["appearances", "participaciones", "apparitions", "مشاركات", "penampilan"],
    ["Laps", "Vueltas", "Tours", "اللفات", "Putaran"],
    ["laps", "vueltas", "tours", "لفات", "putaran"],
    ["Sets", "Sets", "Sets", "الأشواط", "Set"],
    ["sets", "sets", "sets", "أشواط", "set"],
    ["Bouts", "Combates", "Combats", "النزالات", "Duel"],
    ["bouts", "combates", "combats", "نزالات", "duel"],
    ["Snaps", "Jugadas", "Actions", "اللعبات", "Snap"],
    ["snaps", "jugadas", "actions", "لعبات", "snap"],
    ["Points", "Puntos", "Points", "النقاط", "Poin"],
    ["points", "puntos", "points", "نقاط", "poin"],
    ["Wins", "Victorias", "Victoires", "الانتصارات", "Kemenangan"],
    ["wins", "victorias", "victoires", "انتصارات", "kemenangan"],
    ["Podiums", "Podios", "Podiums", "منصات التتويج", "Podium"],
    ["podiums", "podios", "podiums", "منصات تتويج", "podium"],
    ["Fights", "Peleas", "Combats", "النزالات", "Pertarungan"],
    ["fights", "peleas", "combats", "نزالات", "pertarungan"],
    ["Birthplaces", "Lugares de nacimiento", "Lieux de naissance", "أماكن الميلاد", "Tempat lahir"],
    ["Locations", "Ubicaciones", "Lieux", "المواقع", "Lokasi"],
    ["Birth cities", "Ciudades de nacimiento", "Villes de naissance", "مدن الميلاد", "Kota kelahiran"],
    ["Results", "Resultados", "Résultats", "النتائج", "Hasil"],
    ["Location", "Ubicación", "Lieu", "الموقع", "Lokasi"],
    ["locations", "ubicaciones", "lieux", "مواقع", "lokasi"],
    ["Origins", "Orígenes", "Origines", "الأصول", "Asal"],
    ["origin", "origen", "origine", "الأصل", "asal"],
    ["Colleges", "Universidades", "Universités", "الجامعات", "Kampus"],
    ["College", "Universidad", "Université", "الجامعة", "Kampus"],
    ["colleges", "universidades", "universités", "جامعات", "kampus"],
    ["Rankings", "Clasificaciones", "Classements", "التصنيفات", "Peringkat"],
    ["Ranking", "Clasificación", "Classement", "التصنيف", "Peringkat"],
    ["Coverage", "Cobertura", "Couverture", "التغطية", "Cakupan"],
    ["Methodology", "Metodología", "Méthodologie", "المنهجية", "Metodologi"],
    ["About", "Acerca de", "À propos", "حول", "Tentang"],
    ["Source", "Fuente", "Source", "المصدر", "Sumber"],
    ["Data", "Datos", "Données", "البيانات", "Data"],
    ["Season", "Temporada", "Saison", "الموسم", "Musim"],
    ["Source & scope", "Fuente y alcance", "Sources et périmètre", "المصدر والنطاق", "Sumber & cakupan"],
    ["Location coverage", "Cobertura de ubicaciones", "Couverture des lieux", "تغطية المواقع", "Cakupan lokasi"],
    ["Player coverage", "Cobertura de jugadores", "Couverture des joueurs", "تغطية اللاعبين", "Cakupan pemain"],
    ["Driver coverage", "Cobertura de pilotos", "Couverture des pilotes", "تغطية السائقين", "Cakupan pembalap"],
    ["Fighter coverage", "Cobertura de luchadores", "Couverture des combattants", "تغطية المقاتلين", "Cakupan petarung"],
    ["Athlete coverage", "Cobertura de atletas", "Couverture des athlètes", "تغطية الرياضيين", "Cakupan atlet"],
    ["Lap coverage", "Cobertura de vueltas", "Couverture des tours", "تغطية اللفات", "Cakupan putaran"],
    ["Minute coverage", "Cobertura de minutos", "Couverture des minutes", "تغطية الدقائق", "Cakupan menit"],
    ["Minutes coverage", "Cobertura de minutos", "Couverture des minutes", "تغطية الدقائق", "Cakupan menit"],
    ["Bout coverage", "Cobertura de combates", "Couverture des combats", "تغطية النزالات", "Cakupan duel"],
    ["Set coverage", "Cobertura de sets", "Couverture des sets", "تغطية الأشواط", "Cakupan set"],
    ["Game coverage", "Cobertura de partidos", "Couverture des matchs", "تغطية المباريات", "Cakupan pertandingan"],
    ["Snapshot", "Panorama", "Aperçu", "لمحة", "Ringkasan"],
    ["Map", "Mapa", "Carte", "الخريطة", "Peta"],
    ["Population", "Población", "Population", "السكان", "Penduduk"],
    ["Mapped people", "Personas ubicadas", "Personnes localisées", "أشخاص محددو الموقع", "Orang yang dipetakan"],
    ["People", "Personas", "Personnes", "الأشخاص", "Orang"],
    ["workload", "actividad", "activité", "عبء المشاركة", "beban bermain"],
    ["Workload", "Actividad", "Activité", "عبء المشاركة", "Beban bermain"],
    ["per 1M", "por millón", "par million", "لكل مليون", "per juta"],
    ["Open map", "Abrir mapa", "Ouvrir la carte", "افتح الخريطة", "Buka peta"],
    ["Map measures", "Medidas del mapa", "Mesures de la carte", "مقاييس الخريطة", "Ukuran peta"],
    ["Cohort", "Grupo estudiado", "Cohorte", "المجموعة المدروسة", "Kelompok studi"],
    ["Birthplace first", "Primero el lugar de nacimiento", "Lieu de naissance d’abord", "مكان الميلاد أولًا", "Tempat lahir lebih dulu"],
    ["Loading map…", "Cargando mapa…", "Chargement de la carte…", "جارٍ تحميل الخريطة…", "Memuat peta…"],
    ["Loading", "Cargando", "Chargement", "جارٍ التحميل", "Memuat"],
    ["Retry", "Reintentar", "Réessayer", "إعادة المحاولة", "Coba lagi"],
    ["Copy link", "Copiar enlace", "Copier le lien", "نسخ الرابط", "Salin tautan"],
    ["Copied", "Copiado", "Copié", "تم النسخ", "Tersalin"],
    ["Swap", "Intercambiar", "Inverser", "تبديل", "Tukar"],
    ["Swap the two sports", "Intercambiar los deportes", "Inverser les deux sports", "تبديل الرياضتين", "Tukar kedua olahraga"],
    ["Selected area", "Zona seleccionada", "Zone sélectionnée", "المنطقة المحددة", "Wilayah terpilih"],
    ["Clear selected area", "Borrar zona seleccionada", "Effacer la zone sélectionnée", "مسح المنطقة المحددة", "Hapus wilayah terpilih"],
    ["Comparison presets", "Comparaciones predefinidas", "Comparaisons prédéfinies", "مقارنات جاهزة", "Perbandingan cepat"],
    ["Quick comparisons", "Comparaciones rápidas", "Comparaisons rapides", "مقارنات سريعة", "Perbandingan cepat"],
    ["Shared geographic view", "Vista geográfica compartida", "Vue géographique commune", "عرض جغرافي مشترك", "Tampilan geografis bersama"],
    ["Side-by-side explorer", "Explorador en paralelo", "Explorateur côte à côte", "مستكشف جنبًا إلى جنب", "Penjelajah berdampingan"],
    ["All editions", "Todas las ediciones", "Toutes les éditions", "جميع النسخ", "Semua edisi"],
    ["Browse all editions →", "Ver todas las ediciones →", "Parcourir toutes les éditions →", "تصفح جميع النسخ ←", "Jelajahi semua edisi →"],
    ["One world.", "Un mundo.", "Un seul monde.", "عالم واحد.", "Satu dunia."],
    ["Same world.", "El mismo mundo.", "Le même monde.", "العالم نفسه.", "Dunia yang sama."],
    ["Two sporting lenses.", "Dos miradas deportivas.", "Deux regards sportifs.", "منظوران رياضيان.", "Dua sudut pandang olahraga."],
    ["Seventeen sporting lenses.", "Diecisiete miradas deportivas.", "Dix-sept regards sportifs.", "سبعة عشر منظورًا رياضيًا.", "Tujuh belas sudut pandang olahraga."],
  ]);

  rows.push(...[
    ["Part of the Talent Geography project. Data scope matters.", "Parte del proyecto Geografía del Talento. El alcance de los datos importa.", "Un projet Géographie du talent. Le périmètre des données compte.", "جزء من مشروع جغرافيا المواهب. نطاق البيانات مهم.", "Bagian dari proyek Geografi Talenta. Cakupan data itu penting."],
    ["Read data notes →", "Leer notas de datos →", "Lire les notes sur les données →", "اقرأ ملاحظات البيانات ←", "Baca catatan data →"],
    ["Top birthplaces", "Principales lugares de nacimiento", "Principaux lieux de naissance", "أبرز أماكن الميلاد", "Tempat lahir teratas"],
    ["WorldPop 2025", "WorldPop 2025", "WorldPop 2025", "وورلد بوب 2025", "WorldPop 2025"],
    ["Competition", "Competición", "Compétition", "المنافسة", "Kompetisi"],
    ["Cohort method", "Método de selección", "Méthode de sélection", "طريقة اختيار المجموعة", "Metode penentuan kelompok"],
    ["One global map.", "Un mapa global.", "Une carte du monde.", "خريطة عالمية واحدة.", "Satu peta dunia."],
    ["See where the", "Descubre de dónde vienen", "Découvrez d’où viennent", "اكتشف من أين يأتي", "Lihat dari mana"],
    ["Compare the league", "Compara la liga", "Comparer la ligue", "قارن الدوري", "Bandingkan liga"],
    ["Stats", "Estadísticas", "Statistiques", "الإحصاءات", "Statistik"],
    ["Age & geography", "Edad y geografía", "Âge et géographie", "العمر والجغرافيا", "Usia & geografi"],
    ["Age & global mix", "Edad y diversidad mundial", "Âge et diversité mondiale", "العمر والتنوع العالمي", "Usia & keragaman global"],
    ["Age & international mix", "Edad y diversidad internacional", "Âge et diversité internationale", "العمر والتنوع الدولي", "Usia & keragaman internasional"],
    ["Who plays—and where they were born", "Quién juega y dónde nació", "Qui joue et où sont-ils nés", "من يلعب وأين وُلد", "Siapa yang bermain dan di mana mereka lahir"],
    ["Who played—and where they were born", "Quién jugó y dónde nació", "Qui a joué et où sont-ils nés", "من لعب وأين وُلد", "Siapa yang bermain dan di mana mereka lahir"],
    ["Who raced—and where they were born", "Quién compitió y dónde nació", "Qui a couru et où sont-ils nés", "من تسابق وأين وُلد", "Siapa yang membalap dan di mana mereka lahir"],
    ["Who ranks—and where they were born", "Quién está clasificado y dónde nació", "Qui est classé et où sont-ils nés", "من في التصنيف وأين وُلد", "Siapa yang masuk peringkat dan di mana mereka lahir"],
    ["Population-normalized colour scale", "Escala de color ajustada por población", "Échelle de couleurs rapportée à la population", "مقياس ألوان معدل حسب السكان", "Skala warna disesuaikan dengan penduduk"],
    ["2025 snapshot", "Panorama 2025", "Aperçu 2025", "لمحة 2025", "Ringkasan 2025"],
    ["Only verified birthplaces enter population maps", "Solo los lugares de nacimiento verificados entran en los mapas de población", "Seuls les lieux de naissance vérifiés figurent sur les cartes par population", "لا تدخل خرائط السكان سوى أماكن الميلاد الموثّقة", "Hanya tempat lahir terverifikasi masuk ke peta penduduk"],
    ["verified coordinates", "coordenadas verificadas", "coordonnées vérifiées", "إحداثيات موثّقة", "koordinat terverifikasi"],
    ["2025 year-end", "Fin de 2025", "Fin 2025", "نهاية 2025", "Akhir 2025"],
    ["Point coverage", "Cobertura de puntos", "Couverture des points", "تغطية النقاط", "Cakupan poin"],
    ["All teams", "Todos los equipos", "Toutes les équipes", "جميع الفرق", "Semua tim"],
    ["All events", "Todas las pruebas", "Toutes les épreuves", "جميع الفعاليات", "Semua nomor"],
    ["All competitions", "Todas las competiciones", "Toutes les compétitions", "جميع المنافسات", "Semua kompetisi"],
    ["All divisions", "Todas las divisiones", "Toutes les divisions", "جميع الفئات", "Semua divisi"],
    ["All countries", "Todos los países", "Tous les pays", "جميع البلدان", "Semua negara"],
    ["All national teams", "Todas las selecciones", "Toutes les équipes nationales", "جميع المنتخبات الوطنية", "Semua tim nasional"],
    ["All positions", "Todas las posiciones", "Tous les postes", "جميع المراكز", "Semua posisi"],
    ["All four series", "Las cuatro categorías", "Les quatre séries", "جميع الفئات الأربع", "Keempat seri"],
    ["All five series", "Las cinco categorías", "Les cinq séries", "جميع الفئات الخمس", "Kelima seri"],
    ["Both conferences", "Ambas conferencias", "Les deux conférences", "كلتا المجموعتين", "Kedua konferensi"],
    ["Both competitions", "Ambas competiciones", "Les deux compétitions", "كلتا المنافسَتَين", "Kedua kompetisi"],
    ["Both divisions", "Ambas divisiones", "Les deux divisions", "كلتا الفئتين", "Kedua divisi"],
    ["Both tours", "Ambos circuitos", "Les deux circuits", "كلتا الجولتين", "Kedua tur"],
    ["Both rankings", "Ambas clasificaciones", "Les deux classements", "كلا التصنيفين", "Kedua peringkat"],
    ["Men and women", "Hombres y mujeres", "Hommes et femmes", "الرجال والنساء", "Putra dan putri"],
    ["Coordinates", "Coordenadas", "Coordonnées", "الإحداثيات", "Koordinat"],
    ["Regular season", "Temporada regular", "Saison régulière", "الموسم العادي", "Musim reguler"],
    ["Team comparison", "Comparación de equipos", "Comparaison des équipes", "مقارنة الفرق", "Perbandingan tim"],
    ["League-wide", "Toda la liga", "Toute la ligue", "الدوري كاملًا", "Seluruh liga"],
    ["A reproducible completed-season snapshot.", "Una panorámica reproducible de una temporada terminada.", "Un aperçu reproductible d’une saison terminée.", "لمحة قابلة لإعادة الإنتاج عن موسم مكتمل.", "Ringkasan musim selesai yang dapat direproduksi."],
    ["A reproducible season snapshot.", "Una panorámica reproducible de la temporada.", "Un aperçu reproductible de la saison.", "لمحة موسمية قابلة لإعادة الإنتاج.", "Ringkasan musim yang dapat direproduksi."],
    ["Geography", "Geografía", "Géographie", "الجغرافيا", "Geografi"],
    ["Map unavailable until this location clears QA.", "Mapa no disponible hasta que se verifique esta ubicación.", "Carte indisponible tant que ce lieu n’est pas vérifié.", "الخريطة غير متاحة حتى يُراجَع هذا الموقع.", "Peta tidak tersedia sampai lokasi ini lolos pemeriksaan."],
    ["player appearances", "participaciones de jugadores", "apparitions de joueurs", "مشاركات اللاعبين", "penampilan pemain"],
    ["Age", "Edad", "Âge", "العمر", "Usia"],
    ["2025 season", "Temporada 2025", "Saison 2025", "موسم 2025", "Musim 2025"],
    ["Completed 2025 season", "Temporada 2025 terminada", "Saison 2025 terminée", "موسم 2025 المكتمل", "Musim 2025 selesai"],
    ["Comparable geography", "Geografía comparable", "Géographie comparable", "جغرافيا قابلة للمقارنة", "Geografi yang sebanding"],
    ["Keep unresolved birthplace identities visible.", "Mantener visibles las identidades con nacimiento sin resolver.", "Garder visibles les identités dont le lieu de naissance reste inconnu.", "إبقاء هويات أماكن الميلاد غير المحسومة ظاهرة.", "Tampilkan identitas dengan tempat lahir belum diketahui."],
    ["Try Melbourne, London, Monaco…", "Prueba Melbourne, Londres, Mónaco…", "Essayez Melbourne, Londres, Monaco…", "جرّب ملبورن أو لندن أو موناكو…", "Coba Melbourne, London, Monako…"],
    ["Birthplace mix, age and ranking points", "Diversidad de nacimientos, edad y puntos de clasificación", "Origines, âges et points au classement", "تنوع أماكن الميلاد والعمر ونقاط التصنيف", "Sebaran tempat lahir, usia, dan poin peringkat"],
    ["No nationality-to-birthplace substitution", "La nacionalidad no sustituye el lugar de nacimiento", "La nationalité ne remplace pas le lieu de naissance", "لا تُستخدم الجنسية بدل مكان الميلاد", "Kewarganegaraan tidak menggantikan tempat lahir"],
    ["Publish unresolved identities to QA.", "Enviar las identidades sin resolver a revisión.", "Soumettre les identités non résolues à vérification.", "إحالة الهويات غير المحسومة للمراجعة.", "Kirim identitas yang belum teridentifikasi untuk pemeriksaan."],
    ["Rank", "Puesto", "Rang", "الترتيب", "Peringkat"],
    ["Ranking first.", "Primero la clasificación.", "Le classement d’abord.", "التصنيف أولًا.", "Peringkat lebih dulu."],
    ["Ranking points", "Puntos de clasificación", "Points au classement", "نقاط التصنيف", "Poin peringkat"],
    ["ranking points", "puntos de clasificación", "points au classement", "نقاط التصنيف", "poin peringkat"],
    ["2025 regular season", "Temporada regular 2025", "Saison régulière 2025", "الموسم العادي 2025", "Musim reguler 2025"],
    ["2025–26 regular season", "Temporada regular 2025–26", "Saison régulière 2025–26", "الموسم العادي 2025–26", "Musim reguler 2025–26"],
    ["Open snapshot source ↗", "Abrir fuente de datos ↗", "Ouvrir la source des données ↗", "افتح مصدر البيانات ↗", "Buka sumber data ↗"],
    ["Read the data notes", "Leer notas de datos", "Lire les notes sur les données", "اقرأ ملاحظات البيانات", "Baca catatan data"],
    ["Read the maps carefully", "Interpreta los mapas con cuidado", "Lisez les cartes avec prudence", "اقرأ الخرائط بحذر", "Baca peta dengan cermat"],
  ]);

  rows.push(...[
    ["All Sports · Talent Geography", "Todos los deportes · Geografía del talento", "Tous les sports · Géographie du talent", "جميع الرياضات · جغرافيا المواهب", "Semua olahraga · Geografi Talenta"],
    ["All published editions", "Todas las ediciones publicadas", "Toutes les éditions publiées", "جميع النسخ المنشورة", "Semua edisi terbit"],
    ["Open any map, change sport without losing your geographic frame, or put two editions beside each other in the synchronized comparison workspace.", "Abre cualquier mapa, cambia de deporte sin perder el encuadre o compara dos ediciones en paralelo.", "Ouvrez une carte, changez de sport sans perdre votre cadrage ou comparez deux éditions côte à côte.", "افتح أي خريطة وبدّل الرياضة مع الحفاظ على نطاق العرض، أو قارن نسختين جنبًا إلى جنب.", "Buka peta mana pun, ganti olahraga tanpa kehilangan tampilan geografis, atau bandingkan dua edisi berdampingan."],
    ["Compare two sports", "Comparar dos deportes", "Comparer deux sports", "قارن رياضتين", "Bandingkan dua olahraga"],
    ["Same zoom · independent measures", "Mismo zoom · medidas independientes", "Même zoom · mesures indépendantes", "تكبير موحّد · مقاييس مستقلة", "Zoom sama · ukuran berbeda"],
    ["Comparison guidance", "Guía de comparación", "Guide de comparaison", "دليل المقارنة", "Panduan perbandingan"],
    ["Choose two editions", "Elige dos ediciones", "Choisissez deux éditions", "اختر نسختين", "Pilih dua edisi"],
    ["Each sport retains its own cohort and workload measure.", "Cada deporte mantiene su propio grupo y medida de actividad.", "Chaque sport conserve sa cohorte et sa mesure d’activité.", "تحتفظ كل رياضة بمجموعتها ومقياس مشاركتها.", "Tiap olahraga mempertahankan kelompok dan ukuran aktivitasnya."],
    ["Frame the geography", "Encuadra la geografía", "Cadrez la géographie", "حدد النطاق الجغرافي", "Atur cakupan geografis"],
    ["Pan or zoom either map; its companion stays in sync.", "Desplaza o acerca un mapa; el otro se sincroniza.", "Déplacez ou zoomez sur une carte ; l’autre suit.", "حرّك إحدى الخريطتين أو كبّرها؛ وستتزامن الأخرى.", "Geser atau perbesar salah satu peta; peta lain akan mengikuti."],
    ["Compare places or rates", "Compara lugares o tasas", "Comparez les lieux ou les taux", "قارن الأماكن أو المعدلات", "Bandingkan tempat atau rasio"],
    ["Switch both maps between locations and population areas.", "Cambia ambos mapas entre lugares y zonas de población.", "Passez les deux cartes des lieux aux zones de population.", "بدّل الخريطتين بين المواقع والمناطق السكانية.", "Alihkan kedua peta antara lokasi dan wilayah penduduk."],
    ["Sport directory", "Directorio de deportes", "Répertoire des sports", "دليل الرياضات", "Direktori olahraga"],
    ["Explore every map", "Explora todos los mapas", "Explorez toutes les cartes", "استكشف جميع الخرائط", "Jelajahi semua peta"],
    ["Coverage measures verified mapped locations, not sporting participation.", "La cobertura mide ubicaciones verificadas, no la participación deportiva.", "La couverture mesure les lieux vérifiés sur la carte, pas la participation sportive.", "تقيس التغطية المواقع الموثّقة على الخريطة، لا المشاركة الرياضية.", "Cakupan mengukur lokasi terverifikasi yang dipetakan, bukan partisipasi olahraga."],
    ["Compare carefully", "Compara con cuidado", "Comparez avec prudence", "قارن بحذر", "Bandingkan dengan cermat"],
    ["Players, athletes, riders and fighters are directly comparable as people in a defined cohort. Starts, points, snaps, sets, laps and other workload measures retain their sport-specific meanings. Population views use the same WorldPop denominator and area resolutions, but cohort sizes and scopes still differ.", "Jugadores, atletas, pilotos y luchadores pueden compararse como personas de un grupo definido. Titularidades, puntos, jugadas, sets, vueltas y otras medidas conservan el sentido de cada deporte. Las vistas de población usan el mismo denominador de WorldPop y las mismas zonas, pero los tamaños y alcances de los grupos varían.", "Joueurs, athlètes, pilotes et combattants sont comparables en tant que personnes d’une cohorte définie. Titularisations, points, actions, sets, tours et autres mesures gardent un sens propre à chaque sport. Les vues par population utilisent le même dénominateur WorldPop et les mêmes zones, mais la taille et le périmètre des cohortes varient.", "يمكن مقارنة اللاعبين والرياضيين والمتسابقين والمقاتلين بوصفهم أشخاصًا ضمن مجموعات محددة. أما المشاركات والنقاط واللعبات والأشواط واللفات وغيرها فلكل منها معنى خاص برياضتها. تستخدم عروض السكان المقام نفسه من WorldPop وأحجام المناطق نفسها، لكن أحجام المجموعات ونطاقاتها تختلف.", "Pemain, atlet, pembalap, dan petarung dapat dibandingkan sebagai orang dalam kelompok yang jelas. Starter, poin, snap, set, putaran, dan ukuran aktivitas lain memiliki arti khusus tiap olahraga. Tampilan penduduk memakai penyebut WorldPop dan ukuran wilayah yang sama, tetapi ukuran dan cakupan kelompok berbeda."],
    ["Seventeen completed-season views. One reproducible project.", "Diecisiete vistas de temporadas terminadas. Un proyecto reproducible.", "Dix-sept vues de saisons terminées. Un projet reproductible.", "سبعة عشر عرضًا لمواسم مكتملة. مشروع واحد قابل لإعادة الإنتاج.", "Tujuh belas tampilan musim selesai. Satu proyek yang dapat direproduksi."],
    ["Birthplace and origin methodology varies by source.", "La metodología de nacimiento y origen varía según la fuente.", "La méthode concernant naissance et origine varie selon la source.", "تختلف منهجية أماكن الميلاد والأصول بحسب المصدر.", "Metode tempat lahir dan asal berbeda menurut sumber."],
    ["JavaScript is required to load the sport directory.", "Se necesita JavaScript para cargar el directorio de deportes.", "JavaScript est nécessaire pour charger le répertoire des sports.", "يلزم JavaScript لتحميل دليل الرياضات.", "JavaScript diperlukan untuk memuat direktori olahraga."],
    ["Compare Sports · Talent Geography", "Comparar deportes · Geografía del talento", "Comparer les sports · Géographie du talent", "مقارنة الرياضات · جغرافيا المواهب", "Bandingkan olahraga · Geografi Talenta"],
    ["Skip to comparison", "Ir a la comparación", "Aller à la comparaison", "انتقل إلى المقارنة", "Lewati ke perbandingan"],
    ["Synced maps", "Mapas sincronizados", "Cartes synchronisées", "خرائط متزامنة", "Peta tersinkron"],
    ["Cross-sport map comparison", "Comparación de mapas entre deportes", "Comparaison des cartes entre sports", "مقارنة الخرائط بين الرياضات", "Perbandingan peta lintas olahraga"],
    ["Pan or zoom either map and the other follows. Choose each sport’s own workload or its mapped people; circle sizes are scaled within each panel. In the per-1M view, select any hexagon to compare that area.", "Desplaza o acerca un mapa y el otro lo seguirá. Elige la actividad de cada deporte o sus personas ubicadas; el tamaño de los círculos se ajusta en cada panel. En la vista por millón, selecciona un hexágono para comparar esa zona.", "Déplacez ou zoomez sur une carte et l’autre suit. Choisissez l’activité propre à chaque sport ou ses personnes localisées ; la taille des cercles est ajustée par panneau. Dans la vue par million, sélectionnez un hexagone pour comparer cette zone.", "حرّك إحدى الخريطتين أو كبّرها فتتبعها الأخرى. اختر مقياس المشاركة الخاص بكل رياضة أو الأشخاص محددي الموقع؛ ويُضبط حجم الدوائر في كل لوحة على حدة. في عرض المعدل لكل مليون، اختر أي سداسي لمقارنة تلك المنطقة.", "Geser atau perbesar salah satu peta dan peta lain mengikuti. Pilih aktivitas masing-masing olahraga atau orang yang dipetakan; ukuran lingkaran disesuaikan di tiap panel. Pada tampilan per juta, pilih heksagon untuk membandingkan wilayahnya."],
    ["The maps share a viewport and birthplace-first geography, but each panel scales its own symbols and retains its sport-specific cohort and workload unit. In population mode, select a hexagon to compare people per million in the same area. Faint populated-land cells mean zero mapped participants; an unavailable area has no published population cell. Labelled hometown or origin fallbacks are excluded because they are not birthplaces. Rates with fewer than two mapped people or fewer than 100,000 residents are shown as small samples.", "Los mapas comparten vista y priorizan el lugar de nacimiento, pero cada panel ajusta sus símbolos y conserva su grupo y unidad propios. En el modo de población, selecciona un hexágono para comparar personas por millón en la misma zona. Las celdas tenues indican cero participantes ubicados; una zona no disponible carece de datos de población. Se excluyen las ciudades de residencia u orígenes alternativos porque no son lugares de nacimiento. Las tasas con menos de dos personas o 100.000 habitantes se señalan como muestras pequeñas.", "Les cartes partagent une vue et privilégient le lieu de naissance, mais chaque panneau adapte ses symboles et conserve sa cohorte et son unité propres. En mode population, sélectionnez un hexagone pour comparer les personnes par million dans la même zone. Les cellules pâles indiquent zéro participant localisé ; une zone indisponible n’a pas de cellule de population publiée. Les villes d’origine utilisées en remplacement sont exclues car elles ne sont pas des lieux de naissance. Les taux portant sur moins de deux personnes ou 100 000 habitants sont signalés comme petits échantillons.", "تشترك الخريطتان في نطاق العرض وتقدمان مكان الميلاد، لكن كل لوحة تضبط رموزها وتحافظ على مجموعتها ووحدة مشاركتها. في وضع السكان، اختر سداسيًا لمقارنة عدد الأشخاص لكل مليون في المنطقة نفسها. الخلايا الباهتة تعني عدم وجود مشاركين محددي الموقع، والمنطقة غير المتاحة تفتقر إلى خلية سكانية منشورة. تُستبعد بدائل مسقط الرأس أو الأصل لأنها ليست أماكن ميلاد. تُعرض المعدلات التي تضم أقل من شخصين أو 100,000 نسمة بوصفها عينات صغيرة.", "Kedua peta berbagi tampilan dan mengutamakan tempat lahir, tetapi tiap panel menyesuaikan simbolnya sendiri dan mempertahankan kelompok serta satuan aktivitasnya. Dalam mode penduduk, pilih heksagon untuk membandingkan orang per juta di wilayah yang sama. Sel samar berarti nol peserta dipetakan; wilayah yang tidak tersedia tidak punya sel penduduk terbit. Pengganti berupa kampung halaman atau asal dikecualikan karena bukan tempat lahir. Rasio dengan kurang dari dua orang atau 100.000 penduduk ditandai sebagai sampel kecil."],
    ["Seventeen completed-season views. One synchronized comparison.", "Diecisiete temporadas terminadas. Una comparación sincronizada.", "Dix-sept saisons terminées. Une comparaison synchronisée.", "سبعة عشر عرضًا لمواسم مكتملة. مقارنة متزامنة واحدة.", "Tujuh belas tampilan musim selesai. Satu perbandingan tersinkron."],
    ["Choose a geographic view", "Elegir vista geográfica", "Choisir une vue géographique", "اختر عرضًا جغرافيًا", "Pilih tampilan geografis"],
    ["Choose population area size", "Elegir tamaño de zona poblacional", "Choisir la taille des zones de population", "اختر حجم المنطقة السكانية", "Pilih ukuran wilayah penduduk"],
    ["Choose visible comparison map", "Elegir mapa de comparación visible", "Choisir la carte de comparaison visible", "اختر خريطة المقارنة الظاهرة", "Pilih peta perbandingan yang terlihat"],
    ["Selected area comparison", "Comparación de la zona seleccionada", "Comparaison de la zone sélectionnée", "مقارنة المنطقة المحددة", "Perbandingan wilayah terpilih"],
    ["Same area · two sports", "Misma zona · dos deportes", "Même zone · deux sports", "المنطقة نفسها · رياضتان", "Wilayah sama · dua olahraga"],
    ["Per 1M areas", "Zonas por millón", "Zones par million", "مناطق لكل مليون", "Wilayah per juta"],
    ["Places", "Lugares", "Lieux", "الأماكن", "Tempat"],
    ["Very large", "Muy grande", "Très grande", "كبيرة جدًا", "Sangat besar"],
    ["Map A", "Mapa A", "Carte A", "الخريطة أ", "Peta A"],
    ["Map B", "Mapa B", "Carte B", "الخريطة ب", "Peta B"],
    ["Map A measure", "Medida del mapa A", "Mesure de la carte A", "مقياس الخريطة أ", "Ukuran peta A"],
    ["Map B measure", "Medida del mapa B", "Mesure de la carte B", "مقياس الخريطة ب", "Ukuran peta B"],
  ]);

  rows.push(...[
    ["Explore verified birthplaces and, where those are unavailable, clearly labelled football origins behind all 18 clubs.", "Explora los lugares de nacimiento verificados y, cuando falten, los orígenes futbolísticos claramente señalados de los 18 clubes.", "Explorez les lieux de naissance vérifiés et, à défaut, les origines footballistiques clairement indiquées des 18 clubs.", "استكشف أماكن الميلاد الموثّقة، وعند غيابها أصول كرة القدم الموضحة بوضوح للاعبي الأندية الثمانية عشر.", "Jelajahi tempat lahir terverifikasi dan, bila tidak tersedia, asal sepak bola yang diberi label jelas dari 18 klub."],
    ["Birthplace and football origin are different facts. The explorer labels them separately and never infers one from the other.", "Lugar de nacimiento y origen futbolístico son datos distintos. El explorador los distingue y nunca deduce uno del otro.", "Lieu de naissance et origine footballistique sont deux faits distincts. L’explorateur les distingue sans déduire l’un de l’autre.", "مكان الميلاد وأصل كرة القدم حقيقتان مختلفتان؛ يعرضهما المستكشف منفصلين ولا يستنتج أحدهما من الآخر.", "Tempat lahir dan asal sepak bola adalah fakta berbeda. Penjelajah memberi label terpisah dan tidak menyimpulkan salah satunya dari yang lain."],
    ["Verified birthplace where available; otherwise a documented and separately labelled football origin.", "Lugar de nacimiento verificado si existe; en caso contrario, origen futbolístico documentado y señalado por separado.", "Lieu de naissance vérifié si disponible ; sinon, origine footballistique documentée et indiquée séparément.", "مكان ميلاد موثّق إن توفر؛ وإلا فأصل كروي موثّق ومعنون على نحو منفصل.", "Tempat lahir terverifikasi bila tersedia; jika tidak, asal sepak bola terdokumentasi dengan label tersendiri."],
    ["Player-games connected specifically to a verified birthplace. Population maps use only this subset.", "Partidos de jugadores vinculados a un lugar de nacimiento verificado. Los mapas de población usan solo este subconjunto.", "Matchs de joueurs liés à un lieu de naissance vérifié. Les cartes par population n’utilisent que ce sous-ensemble.", "مباريات اللاعبين المرتبطة تحديدًا بمكان ميلاد موثّق. تستخدم خرائط السكان هذه المجموعة الفرعية فقط.", "Pertandingan pemain yang terhubung khusus ke tempat lahir terverifikasi. Peta penduduk hanya memakai bagian ini."],
    ["Player-game totals come from AFL Tables via fitzRoy. Birthplaces come from Wikidata and explicit Wikipedia infobox fields. Football origins come from Wikipedia original-team fields and are geocoded via Wikidata. Population estimates use verified birthplaces only.", "Los partidos proceden de AFL Tables mediante fitzRoy. Los nacimientos provienen de Wikidata y fichas de Wikipedia. Los orígenes futbolísticos provienen del campo de equipo original de Wikipedia y se geocodifican con Wikidata. Las estimaciones de población usan solo nacimientos verificados.", "Les matchs viennent d’AFL Tables via fitzRoy. Les lieux de naissance viennent de Wikidata et des infobox Wikipédia. Les origines footballistiques viennent des équipes d’origine indiquées sur Wikipédia et sont géocodées via Wikidata. Les estimations de population n’utilisent que les naissances vérifiées.", "تأتي المباريات من AFL Tables عبر fitzRoy، وأماكن الميلاد من Wikidata وحقول ويكيبيديا الصريحة. وتأتي الأصول الكروية من حقول الفريق الأصلي في ويكيبيديا وتُحدّد إحداثياتها عبر Wikidata. تستخدم تقديرات السكان أماكن الميلاد الموثّقة فقط.", "Jumlah pertandingan berasal dari AFL Tables melalui fitzRoy. Tempat lahir berasal dari Wikidata dan kolom infobox Wikipedia. Asal sepak bola berasal dari kolom tim asal Wikipedia dan diberi koordinat melalui Wikidata. Perkiraan penduduk hanya memakai tempat lahir terverifikasi."],
    ["Explore verified birthplaces behind the athletes who competed at the 2025 World Athletics Championships.", "Explora los lugares de nacimiento verificados de quienes compitieron en el Mundial de Atletismo 2025.", "Explorez les lieux de naissance vérifiés des athlètes des Championnats du monde d’athlétisme 2025.", "استكشف أماكن الميلاد الموثّقة للرياضيين المشاركين في بطولة العالم لألعاب القوى 2025.", "Jelajahi tempat lahir terverifikasi atlet Kejuaraan Dunia Atletik 2025."],
    ["An event entry counts once per athlete and event. Qualification rounds, finals and combined-event disciplines do not inflate the primary workload.", "Cada inscripción cuenta una vez por atleta y prueba. Clasificatorias, finales y disciplinas combinadas no inflan la medida principal.", "Chaque engagement compte une fois par athlète et épreuve. Qualifications, finales et disciplines combinées ne gonflent pas la mesure principale.", "تُحسب مشاركة واحدة لكل رياضي وفعالية. ولا تزيد الأدوار التأهيلية والنهائيات وتخصصات الفعاليات المركبة عبء المشاركة الأساسي.", "Keikutsertaan dihitung sekali per atlet dan nomor. Babak kualifikasi, final, dan disiplin gabungan tidak menggandakan ukuran utama."],
    ["Official World Athletics results define the cohort, rounds, relay lineups and medals. Birthplaces come from Wikidata identities matched by World Athletics ID or exact name and date of birth.", "Los resultados oficiales de World Athletics definen el grupo, las rondas, los relevos y las medallas. Los nacimientos proceden de identidades de Wikidata vinculadas por ID o nombre y fecha de nacimiento exactos.", "Les résultats officiels de World Athletics définissent la cohorte, les tours, les relais et les médailles. Les naissances viennent d’identités Wikidata associées par identifiant ou nom et date de naissance exacts.", "تحدد نتائج World Athletics الرسمية المجموعة والأدوار وتشكيلات التتابع والميداليات. وتأتي أماكن الميلاد من هويات Wikidata المطابقة بمعرّف World Athletics أو الاسم وتاريخ الميلاد الدقيقين.", "Hasil resmi World Athletics menentukan kelompok, babak, susunan estafet, dan medali. Tempat lahir berasal dari identitas Wikidata yang dicocokkan lewat ID World Athletics atau nama dan tanggal lahir persis."],
    ["Explore the birthplaces behind the top 100 singles players and top 50 pairs in each doubles discipline, measured by athletes or allocated ranking points.", "Explora los nacimientos de los 100 mejores individuales y las 50 mejores parejas de cada modalidad de dobles, por atletas o puntos repartidos.", "Explorez les naissances des 100 meilleurs joueurs en simple et des 50 meilleures paires de chaque discipline de double, par athlètes ou points répartis.", "استكشف أماكن ميلاد أفضل 100 لاعب فردي وأفضل 50 زوجًا في كل فئة زوجية، حسب الرياضيين أو نقاط التصنيف الموزعة.", "Jelajahi tempat lahir 100 pemain tunggal teratas dan 50 pasangan teratas di tiap disiplin ganda, menurut atlet atau poin peringkat yang dialokasikan."],
    ["A pair remains the ranked unit. For geography only, its points are divided equally between both partners; athletes appearing in multiple events are counted once.", "La pareja sigue siendo la unidad clasificada. Solo para la geografía, sus puntos se reparten por igual entre integrantes; cada atleta se cuenta una vez aunque compita en varias pruebas.", "La paire reste l’unité classée. Pour la géographie seulement, ses points sont partagés également entre partenaires ; les athlètes de plusieurs épreuves sont comptés une fois.", "يبقى الزوج وحدة التصنيف. ولأغراض الجغرافيا فقط تُقسم نقاطه بالتساوي بين الشريكين؛ ويُحسب الرياضي مرة واحدة ولو شارك في أكثر من فعالية.", "Pasangan tetap menjadi unit peringkat. Khusus untuk geografi, poinnya dibagi rata kepada kedua pasangan; atlet yang ikut beberapa nomor dihitung sekali."],
    ["The 2025 year-end ranking is BWF week 1 of 2026 because 30 December falls in that ISO week. Ranking points are rolling 52-week totals, not calendar-year points earned.", "La clasificación final de 2025 corresponde a la semana 1 de 2026 de BWF porque el 30 de diciembre cae en esa semana ISO. Los puntos suman 52 semanas móviles, no solo el año natural.", "Le classement de fin 2025 est celui de la semaine 1 de 2026 de la BWF, car le 30 décembre tombe dans cette semaine ISO. Les points couvrent 52 semaines glissantes, pas la seule année civile.", "تصنيف نهاية 2025 هو الأسبوع الأول لعام 2026 لدى BWF لأن 30 ديسمبر يقع في ذلك الأسبوع وفق ISO. النقاط مجموع متحرك لـ52 أسبوعًا، لا نقاط السنة التقويمية فقط.", "Peringkat akhir 2025 adalah pekan 1 BWF tahun 2026 karena 30 Desember masuk pekan ISO tersebut. Poin peringkat adalah total bergulir 52 minggu, bukan poin yang diperoleh dalam tahun kalender."],
    ["Wikidata identities are matched through the official BWF player ID before birthplace coordinates are accepted.", "Las identidades de Wikidata se vinculan mediante el ID oficial BWF antes de aceptar coordenadas de nacimiento.", "Les identités Wikidata sont associées par l’identifiant officiel BWF avant d’accepter les coordonnées de naissance.", "تُطابق هويات Wikidata عبر معرّف اللاعب الرسمي من BWF قبل قبول إحداثيات مكان الميلاد.", "Identitas Wikidata dicocokkan melalui ID pemain resmi BWF sebelum koordinat tempat lahir diterima."],
    ["Explore the birthplaces behind men's and women's T20 internationals involving ICC Full Member teams, measured by player appearances or unique cricketers.", "Explora los nacimientos en los T20 internacionales masculinos y femeninos de miembros plenos de la ICC, por apariciones o jugadores únicos.", "Explorez les naissances dans les T20 internationaux masculins et féminins des membres de plein droit de l’ICC, par apparitions ou joueurs uniques.", "استكشف أماكن الميلاد في مباريات T20 الدولية للرجال والنساء بمشاركة الأعضاء الكاملين في ICC، حسب المشاركات أو لاعبي الكريكيت الفريدين.", "Jelajahi tempat lahir dalam pertandingan T20 internasional putra dan putri anggota penuh ICC, menurut penampilan atau pemain kriket unik."],
    ["Men's and women's schedules contain different numbers of matches. Compare geography and coverage—not raw totals as though the calendars were equal.", "Los calendarios masculino y femenino tienen distinta cantidad de partidos. Compara geografía y cobertura, no totales brutos como si los calendarios fueran iguales.", "Les calendriers masculin et féminin comptent des nombres de matchs différents. Comparez géographie et couverture, pas les totaux bruts comme si les calendriers étaient identiques.", "يختلف عدد المباريات بين جدولي الرجال والنساء. قارن الجغرافيا والتغطية، لا المجاميع الخام كما لو كان الجدولان متماثلين.", "Jadwal putra dan putri memiliki jumlah pertandingan berbeda. Bandingkan geografi dan cakupan, bukan total mentah seolah jadwalnya sama."],
    ["The archive contains different men's and women's schedules, so raw comparison totals reflect both geography and opportunity. Birthplace is never inferred from the represented team.", "El archivo contiene calendarios distintos para hombres y mujeres, por lo que los totales reflejan geografía y oportunidades. Nunca se deduce el nacimiento del equipo representado.", "L’archive contient des calendriers masculin et féminin différents ; les totaux reflètent donc géographie et occasions de jouer. Le lieu de naissance n’est jamais déduit de l’équipe représentée.", "يضم الأرشيف جدولين مختلفين للرجال والنساء؛ لذا تعكس المجاميع الجغرافيا وفرص المشاركة معًا. ولا يُستنتج مكان الميلاد من الفريق المُمثَّل.", "Arsip berisi jadwal putra dan putri berbeda, sehingga total mencerminkan geografi dan peluang bermain. Tempat lahir tidak disimpulkan dari tim yang diwakili."],
    ["Cricsheet UUIDs connect to ESPNcricinfo IDs, then Wikidata and explicit Wikipedia birthplace fields.", "Los UUID de Cricsheet se conectan con IDs de ESPNcricinfo y después con Wikidata y campos explícitos de Wikipedia.", "Les UUID Cricsheet sont reliés aux identifiants ESPNcricinfo, puis à Wikidata et aux champs de naissance explicites de Wikipédia.", "تُربط معرّفات Cricsheet بمعرّفات ESPNcricinfo، ثم بـWikidata وحقول أماكن الميلاد الصريحة في ويكيبيديا.", "UUID Cricsheet ditautkan ke ID ESPNcricinfo, lalu ke Wikidata dan kolom tempat lahir eksplisit di Wikipedia."],
  ]);

  rows.push(...[
    ["Explore the verified birthplaces behind the drivers who started championship races in Formula 1, Formula 2, Formula 3 and the women-focused F1 Academy during 2025.", "Explora los lugares de nacimiento verificados de quienes corrieron en Fórmula 1, Fórmula 2, Fórmula 3 y F1 Academy femenina durante 2025.", "Explorez les naissances vérifiées des pilotes ayant pris le départ en Formule 1, 2, 3 et F1 Academy féminine en 2025.", "استكشف أماكن الميلاد الموثّقة للسائقين الذين بدأوا سباقات فورمولا 1 و2 و3 وأكاديمية F1 النسائية في 2025.", "Jelajahi tempat lahir terverifikasi pembalap yang memulai balapan Formula 1, Formula 2, Formula 3, dan F1 Academy putri sepanjang 2025."],
    ["Laps and starts can be compared across all four series. Championship points remain profile context because each series uses a different scoring system.", "Vueltas y salidas pueden compararse entre las cuatro categorías. Los puntos del campeonato quedan como contexto porque cada categoría usa otro sistema.", "Tours et départs sont comparables entre les quatre séries. Les points de championnat restent contextuels car les barèmes diffèrent.", "يمكن مقارنة اللفات والانطلاقات بين الفئات الأربع. تبقى نقاط البطولة ضمن سياق الملف لأن لكل فئة نظام تسجيل مختلفًا.", "Putaran dan start dapat dibandingkan di keempat seri. Poin kejuaraan tetap menjadi konteks profil karena tiap seri memakai sistem skor berbeda."],
    ["Race classifications cover Formula 1, Formula 2, Formula 3 and F1 Academy. Practice, qualifying and cancelled races are excluded. Birthplaces come from exact linked Wikidata identities.", "Las clasificaciones cubren Fórmula 1, 2, 3 y F1 Academy. Se excluyen entrenamientos, clasificación y carreras canceladas. Los nacimientos proceden de identidades exactas de Wikidata.", "Les classements couvrent Formule 1, 2, 3 et F1 Academy. Essais, qualifications et courses annulées sont exclus. Les naissances proviennent d’identités Wikidata précisément liées.", "تشمل النتائج فورمولا 1 و2 و3 وأكاديمية F1، وتستبعد التجارب والتصفيات والسباقات الملغاة. تأتي أماكن الميلاد من هويات Wikidata المرتبطة بدقة.", "Klasifikasi balapan mencakup Formula 1, 2, 3, dan F1 Academy. Latihan, kualifikasi, dan balapan batal dikecualikan. Tempat lahir berasal dari identitas Wikidata yang ditautkan secara tepat."],
    ["Explore the verified birthplaces behind riders who started 2025 races in MotoGP, Moto2, Moto3, MotoE and the parallel women-only WorldWCR championship.", "Explora los nacimientos verificados de quienes salieron en MotoGP, Moto2, Moto3, MotoE y el campeonato femenino WorldWCR de 2025.", "Explorez les naissances vérifiées des pilotes partis en MotoGP, Moto2, Moto3, MotoE et dans le championnat féminin WorldWCR en 2025.", "استكشف أماكن الميلاد الموثّقة للمتسابقين الذين بدأوا سباقات 2025 في MotoGP وMoto2 وMoto3 وMotoE وبطولة WorldWCR النسائية.", "Jelajahi tempat lahir terverifikasi pembalap yang memulai balapan 2025 di MotoGP, Moto2, Moto3, MotoE, dan kejuaraan putri WorldWCR."],
    ["Laps and starts can be compared across all five series. Championship points remain profile context because each series uses a different scoring system.", "Vueltas y salidas pueden compararse entre las cinco categorías. Los puntos quedan como contexto porque cada categoría usa otro sistema.", "Tours et départs sont comparables entre les cinq séries. Les points restent contextuels car les barèmes diffèrent.", "يمكن مقارنة اللفات والانطلاقات بين الفئات الخمس. تبقى نقاط البطولة ضمن سياق الملف لأن أنظمة التسجيل تختلف.", "Putaran dan start dapat dibandingkan di kelima seri. Poin kejuaraan tetap menjadi konteks profil karena sistem skornya berbeda."],
    ["Race classifications cover MotoGP, Moto2, Moto3, MotoE and WorldWCR. Practice, qualifying and cancelled races are excluded. Birthplaces use official profiles, exact-DOB Wikidata matches and conservative GeoNames resolution.", "Las clasificaciones cubren MotoGP, Moto2, Moto3, MotoE y WorldWCR. Se excluyen entrenamientos, clasificación y carreras canceladas. Los nacimientos usan perfiles oficiales, coincidencias de Wikidata por fecha exacta y GeoNames con cautela.", "Les classements couvrent MotoGP, Moto2, Moto3, MotoE et WorldWCR. Essais, qualifications et courses annulées sont exclus. Les naissances utilisent les profils officiels, des correspondances Wikidata à date exacte et GeoNames avec prudence.", "تشمل النتائج MotoGP وMoto2 وMoto3 وMotoE وWorldWCR، وتستبعد التجارب والتصفيات والسباقات الملغاة. تعتمد أماكن الميلاد على الملفات الرسمية ومطابقات Wikidata الدقيقة وGeoNames بتحفظ.", "Klasifikasi mencakup MotoGP, Moto2, Moto3, MotoE, dan WorldWCR. Latihan, kualifikasi, dan balapan batal dikecualikan. Tempat lahir memakai profil resmi, kecocokan Wikidata dengan tanggal lahir tepat, dan pencocokan GeoNames yang hati-hati."],
    ["Explore the birthplaces behind the men’s and women’s top 100, measured by golfers or year-end ranking points.", "Explora los nacimientos de los 100 mejores hombres y mujeres, por golfistas o puntos de clasificación final.", "Explorez les naissances des 100 meilleurs hommes et femmes, par golfeurs ou points au classement final.", "استكشف أماكن ميلاد أفضل 100 رجل وامرأة، حسب لاعبي الغولف أو نقاط تصنيف نهاية العام.", "Jelajahi tempat lahir 100 pegolf putra dan putri teratas, menurut pegolf atau poin peringkat akhir tahun."],
    ["OWGR and WWGR are separate point systems. Use the ranking filter for direct point comparisons; birthplace is not represented nationality or residence.", "OWGR y WWGR usan sistemas distintos. Filtra por clasificación para comparar puntos; nacimiento no equivale a nacionalidad ni residencia.", "OWGR et WWGR ont des barèmes distincts. Filtrez par classement pour comparer les points ; naissance ne signifie ni nationalité ni résidence.", "يستخدم تصنيفا OWGR وWWGR نظامي نقاط منفصلين. استخدم مرشح التصنيف للمقارنة المباشرة؛ مكان الميلاد ليس الجنسية أو محل الإقامة.", "OWGR dan WWGR memakai sistem poin terpisah. Gunakan filter peringkat untuk membandingkan poin; tempat lahir bukan kewarganegaraan atau tempat tinggal."],
    ["OWGR is dated 28 December and WWGR 29 December 2025. Their points are rolling ranking totals, not calendar-year points earned.", "OWGR está fechado el 28 y WWGR el 29 de diciembre de 2025. Sus puntos son totales móviles, no puntos ganados solo en el año natural.", "L’OWGR date du 28 décembre et le WWGR du 29 décembre 2025. Les points sont des totaux glissants, pas ceux de la seule année civile.", "يعود OWGR إلى 28 ديسمبر وWWGR إلى 29 ديسمبر 2025. نقاطهما مجموع تصنيف متحرك، لا نقاط السنة التقويمية وحدها.", "OWGR bertanggal 28 Desember dan WWGR 29 Desember 2025. Poinnya adalah total peringkat bergulir, bukan poin yang diraih hanya selama tahun kalender."],
    ["Ranking IDs or exact golfer pages are checked before explicit birthplace coordinates are accepted.", "Se comprueban IDs de clasificación o páginas exactas antes de aceptar coordenadas de nacimiento.", "Les identifiants de classement ou pages exactes des golfeurs sont vérifiés avant d’accepter les coordonnées de naissance.", "تُفحص معرّفات التصنيف أو صفحات لاعبي الغولف الدقيقة قبل قبول إحداثيات الميلاد.", "ID peringkat atau halaman pegolf yang tepat diperiksa sebelum koordinat tempat lahir diterima."],
    ["Explore the birthplaces behind the men’s and women’s individual top 100, measured by players or year-end FIP ranking points.", "Explora los nacimientos de los 100 mejores hombres y mujeres, por jugadores o puntos FIP de fin de año.", "Explorez les naissances des 100 meilleurs hommes et femmes, par joueurs ou points FIP de fin d’année.", "استكشف أماكن ميلاد أفضل 100 لاعب ولاعبة، حسب اللاعبين أو نقاط تصنيف FIP بنهاية العام.", "Jelajahi tempat lahir 100 pemain putra dan putri teratas, menurut pemain atau poin peringkat FIP akhir tahun."],
    ["Padel is played in pairs, but FIP ranks each player individually. Use the division filter for point comparisons; birthplace is not represented nationality.", "El pádel se juega en parejas, pero FIP clasifica a cada jugador por separado. Filtra por división para comparar puntos; nacimiento no equivale a nacionalidad representada.", "Le padel se joue en double, mais la FIP classe chaque joueur séparément. Filtrez par division pour comparer les points ; naissance ne signifie pas nationalité représentée.", "تُلعب البادل في أزواج، لكن FIP يصنف كل لاعب منفردًا. استخدم مرشح الفئة لمقارنة النقاط؛ مكان الميلاد ليس الجنسية الممثلة.", "Padel dimainkan berpasangan, tetapi FIP memberi peringkat tiap pemain secara individu. Gunakan filter divisi untuk membandingkan poin; tempat lahir bukan kewarganegaraan yang diwakili."],
    ["The cohort represents the final 2025 ranking dated 22 December. The women’s rows are taken from FIP’s unchanged opening-2026 carry-forward because its rebuilt endpoint no longer returns that archived table.", "El grupo refleja la clasificación final de 2025 del 22 de diciembre. Las filas femeninas proceden del arrastre sin cambios de FIP al inicio de 2026 porque su nuevo servicio ya no devuelve la tabla archivada.", "La cohorte reflète le classement final 2025 du 22 décembre. Les lignes féminines viennent du report inchangé début 2026 de la FIP, son nouveau service ne renvoyant plus l’archive.", "تمثل المجموعة تصنيف 2025 النهائي بتاريخ 22 ديسمبر. أُخذت صفوف النساء من ترحيل FIP غير المتغير لبداية 2026 لأن واجهتها الجديدة لم تعد توفر الجدول المؤرشف.", "Kelompok mewakili peringkat akhir 2025 tanggal 22 Desember. Baris putri diambil dari data bawaan awal 2026 FIP yang belum berubah karena layanan barunya tidak lagi mengembalikan tabel arsip."],
    ["The official FIP profile supplies the player ID, DOB and birthplace label; GeoNames supplies only the coordinates.", "El perfil oficial FIP aporta ID, fecha y lugar de nacimiento; GeoNames solo aporta coordenadas.", "Le profil officiel FIP fournit l’identifiant, la date et le lieu de naissance ; GeoNames fournit seulement les coordonnées.", "يوفر ملف FIP الرسمي معرّف اللاعب وتاريخ ومكان الميلاد؛ ويوفر GeoNames الإحداثيات فقط.", "Profil resmi FIP menyediakan ID pemain, tanggal lahir, dan nama tempat lahir; GeoNames hanya menyediakan koordinat."],
    ["Explore the birthplaces behind the men’s and women’s singles top 100, measured by players or year-end ranking points.", "Explora los nacimientos de los 100 mejores en individuales masculino y femenino, por jugadores o puntos de fin de año.", "Explorez les naissances des 100 meilleurs en simple hommes et femmes, par joueurs ou points de fin d’année.", "استكشف أماكن ميلاد أفضل 100 لاعب ولاعبة في الفردي، حسب اللاعبين أو نقاط نهاية العام.", "Jelajahi tempat lahir 100 pemain tunggal putra dan putri teratas, menurut pemain atau poin peringkat akhir tahun."],
    ["ATP and WTA points are separate ranking systems. Use the tour filter for direct point comparisons; birthplace is not represented nationality.", "Los puntos ATP y WTA son sistemas distintos. Filtra por circuito para comparar puntos; nacimiento no equivale a nacionalidad representada.", "Les points ATP et WTA relèvent de classements distincts. Filtrez par circuit pour comparer les points ; naissance ne signifie pas nationalité représentée.", "نقاط ATP وWTA نظاما تصنيف منفصلان. استخدم مرشح الجولة لمقارنة النقاط مباشرة؛ مكان الميلاد ليس الجنسية الممثلة.", "Poin ATP dan WTA adalah sistem peringkat terpisah. Gunakan filter tur untuk membandingkan poin; tempat lahir bukan kewarganegaraan yang diwakili."],
    ["The ATP list is dated 17 November 2025 and the WTA list 10 November 2025. Points are rolling ranking totals, not every point earned during the calendar year.", "La lista ATP es del 17 y la WTA del 10 de noviembre de 2025. Los puntos son totales móviles, no todos los ganados durante el año natural.", "La liste ATP date du 17 novembre 2025 et la WTA du 10 novembre. Les points sont des totaux glissants, pas tous ceux gagnés pendant l’année civile.", "قائمة ATP بتاريخ 17 نوفمبر 2025 وقائمة WTA بتاريخ 10 نوفمبر. النقاط مجموع تصنيف متحرك، لا كل نقاط السنة التقويمية.", "Daftar ATP bertanggal 17 November 2025 dan WTA 10 November 2025. Poin adalah total peringkat bergulir, bukan semua poin yang diraih selama tahun kalender."],
    ["Stable tour IDs or exact names are checked against player DOB before Wikidata coordinates are accepted.", "Se comprueban IDs estables o nombres exactos con la fecha de nacimiento antes de aceptar coordenadas de Wikidata.", "Les identifiants stables ou noms exacts sont vérifiés avec la date de naissance avant d’accepter les coordonnées Wikidata.", "تُفحص معرّفات الجولة الثابتة أو الأسماء الدقيقة مقابل تاريخ الميلاد قبل قبول إحداثيات Wikidata.", "ID tur yang stabil atau nama persis diperiksa terhadap tanggal lahir sebelum koordinat Wikidata diterima."],
  ]);

  rows.push(...[
    ["Explore the birthplaces behind all 30 clubs, compare leagues and teams, then open any hitter or pitcher for their season workload.", "Explora los nacimientos de los 30 clubes, compara ligas y equipos y consulta la actividad de bateadores y lanzadores.", "Explorez les naissances des 30 clubs, comparez ligues et équipes, puis consultez l’activité des frappeurs et lanceurs.", "استكشف أماكن ميلاد لاعبي الأندية الثلاثين، وقارن الدوريات والفرق، وافتح ملف أي ضارب أو رامٍ لرؤية مشاركته الموسمية.", "Jelajahi tempat lahir di 30 klub, bandingkan liga dan tim, lalu buka pemain pemukul atau pelempar untuk melihat aktivitas musimannya."],
    ["Includes every player with at least one 2025 regular-season appearance. Birthplace is not nationality or where a player developed.", "Incluye a quienes disputaron al menos un partido de la temporada regular 2025. Nacimiento no equivale a nacionalidad ni lugar de formación.", "Inclut tout joueur ayant participé à la saison régulière 2025. Naissance ne signifie ni nationalité ni lieu de formation.", "يشمل كل لاعب شارك مرة واحدة على الأقل في موسم 2025 العادي. مكان الميلاد ليس الجنسية أو مكان تطور اللاعب.", "Mencakup semua pemain dengan setidaknya satu penampilan musim reguler 2025. Tempat lahir bukan kewarganegaraan atau tempat pemain berkembang."],
    ["Team totals and recorded birthplaces come from MLB's official Stats API. Coordinates come from GeoNames; local population estimates come from WorldPop.", "Los totales y nacimientos proceden de la API oficial de MLB. Las coordenadas vienen de GeoNames y la población local de WorldPop.", "Les totaux et naissances viennent de l’API officielle MLB. Les coordonnées viennent de GeoNames et les populations locales de WorldPop.", "تأتي مجاميع الفرق وأماكن الميلاد المسجلة من واجهة إحصاءات MLB الرسمية، والإحداثيات من GeoNames، وتقديرات السكان المحليين من WorldPop.", "Total tim dan tempat lahir tercatat berasal dari Stats API resmi MLB. Koordinat dari GeoNames; perkiraan penduduk lokal dari WorldPop."],
    ["Explore the birthplaces behind all 30 teams, compare conferences and clubs, then open any player for season totals.", "Explora los nacimientos de los 30 equipos, compara conferencias y clubes y consulta los totales de temporada de cada jugador.", "Explorez les naissances des 30 équipes, comparez conférences et clubs, puis consultez les totaux de saison de chaque joueur.", "استكشف أماكن ميلاد لاعبي الفرق الثلاثين، وقارن المجموعات والأندية، وافتح ملف أي لاعب لرؤية مجاميع موسمه.", "Jelajahi tempat lahir di 30 tim, bandingkan konferensi dan klub, lalu buka pemain untuk melihat total musimnya."],
    ["Includes every player with at least one 2025–26 regular-season appearance. Birthplace is not the same as nationality or where a player developed.", "Incluye a quienes disputaron al menos un partido de la temporada regular 2025–26. Nacimiento no equivale a nacionalidad ni lugar de formación.", "Inclut tout joueur ayant participé à la saison régulière 2025–26. Naissance ne signifie ni nationalité ni lieu de formation.", "يشمل كل لاعب شارك مرة واحدة على الأقل في الموسم العادي 2025–26. مكان الميلاد لا يساوي الجنسية أو مكان تطور اللاعب.", "Mencakup semua pemain dengan setidaknya satu penampilan musim reguler 2025–26. Tempat lahir tidak sama dengan kewarganegaraan atau tempat pemain berkembang."],
    ["NBA player IDs matched to Wikidata birthplace entities with geographic coordinates.", "IDs de jugadores NBA vinculados a lugares de nacimiento de Wikidata con coordenadas.", "Identifiants NBA associés aux lieux de naissance Wikidata avec coordonnées.", "طُوبقت معرّفات لاعبي NBA مع كيانات أماكن الميلاد في Wikidata وإحداثياتها.", "ID pemain NBA dicocokkan dengan entitas tempat lahir Wikidata yang memiliki koordinat."],
    ["Regular-season totals come from the NBA Stats API, using a public API export as the reproducible snapshot. Player identity and birthplace geography come from Wikidata; local population estimates come from WorldPop.", "Los totales de temporada vienen de NBA Stats API mediante una exportación pública reproducible. Identidad y nacimiento proceden de Wikidata; población local de WorldPop.", "Les totaux de saison viennent de l’API NBA Stats via un export public reproductible. Identité et lieux de naissance viennent de Wikidata ; populations locales de WorldPop.", "تأتي مجاميع الموسم من واجهة NBA Stats عبر تصدير عام قابل لإعادة الإنتاج. وتأتي الهوية وأماكن الميلاد من Wikidata، وتقديرات السكان المحليين من WorldPop.", "Total musim berasal dari NBA Stats API melalui ekspor publik yang dapat direproduksi. Identitas dan tempat lahir berasal dari Wikidata; perkiraan penduduk lokal dari WorldPop."],
    ["Map every player who stepped onto the field by birthplace or college, compare all 32 teams, and see which places produce the league’s playing time.", "Ubica a todos los jugadores por nacimiento o universidad, compara los 32 equipos y observa qué lugares aportan tiempo de juego.", "Cartographiez chaque joueur par naissance ou université, comparez les 32 équipes et voyez quels lieux fournissent le temps de jeu.", "ضع كل لاعب دخل الملعب على الخريطة حسب مكان ميلاده أو جامعته، وقارن الفرق الـ32 واعرف الأماكن التي تنتج وقت اللعب.", "Petakan setiap pemain yang turun ke lapangan menurut tempat lahir atau kampus, bandingkan 32 tim, dan lihat tempat yang menghasilkan waktu bermain."],
    ["Includes players with at least one offensive, defensive or special-teams snap in the 2025 regular season. Birthplace and college are separate location lenses.", "Incluye a quienes jugaron al menos una jugada ofensiva, defensiva o de equipos especiales en 2025. Nacimiento y universidad son perspectivas separadas.", "Inclut les joueurs avec au moins une action offensive, défensive ou d’équipes spéciales en 2025. Naissance et université sont deux vues distinctes.", "يشمل اللاعبين الذين خاضوا لعبة هجومية أو دفاعية أو لفرق خاصة واحدة على الأقل في موسم 2025 العادي. مكان الميلاد والجامعة منظوران منفصلان للموقع.", "Mencakup pemain dengan setidaknya satu snap menyerang, bertahan, atau tim khusus pada musim reguler 2025. Tempat lahir dan kampus adalah dua sudut pandang lokasi terpisah."],
    ["Playing time and college histories come from nflverse. Birth cities and college home venues come from ESPN; coordinates use GeoNames with four College Scorecard campus fallbacks.", "El tiempo de juego y las trayectorias universitarias vienen de nflverse. Ciudades de nacimiento y sedes universitarias vienen de ESPN; las coordenadas usan GeoNames con cuatro alternativas de College Scorecard.", "Le temps de jeu et les parcours universitaires viennent de nflverse. Villes de naissance et campus viennent d’ESPN ; les coordonnées utilisent GeoNames et quatre solutions de repli College Scorecard.", "يأتي وقت اللعب والتاريخ الجامعي من nflverse، ومدن الميلاد ومواقع الجامعات من ESPN؛ وتستخدم الإحداثيات GeoNames مع أربع بدائل جامعية من College Scorecard.", "Waktu bermain dan riwayat kampus berasal dari nflverse. Kota lahir dan lokasi kampus dari ESPN; koordinat memakai GeoNames dengan empat cadangan kampus College Scorecard."],
    ["Use the first listed nflverse college as the primary/final program, retaining the full transfer history.", "Se usa la primera universidad indicada por nflverse como programa principal/final y se conserva el historial completo de traspasos.", "La première université de nflverse est retenue comme programme principal/final, tout en gardant l’historique complet des transferts.", "تُستخدم الجامعة الأولى في قائمة nflverse بوصفها البرنامج الأساسي/النهائي، مع الاحتفاظ بتاريخ الانتقالات الكامل.", "Kampus pertama di daftar nflverse dipakai sebagai program utama/terakhir, sambil mempertahankan seluruh riwayat transfer."],
    ["Map birthplace and college program independently; unresolved locations remain out of map totals.", "Se cartografían nacimiento y universidad por separado; las ubicaciones sin resolver no entran en los totales.", "Naissance et université sont cartographiées séparément ; les lieux non résolus restent hors des totaux.", "تُرسم أماكن الميلاد والجامعات كلٌّ على حدة؛ وتُستبعد المواقع غير المحسومة من مجاميع الخرائط.", "Tempat lahir dan kampus dipetakan terpisah; lokasi yang belum teridentifikasi tidak masuk total peta."],
    ["Explore the birthplaces behind all 32 teams, compare conferences and clubs, then open any skater or goalie for season totals.", "Explora los nacimientos de los 32 equipos, compara conferencias y clubes y consulta los totales de patinadores y porteros.", "Explorez les naissances des 32 équipes, comparez conférences et clubs, puis consultez les totaux des patineurs et gardiens.", "استكشف أماكن ميلاد لاعبي الفرق الـ32، وقارن المجموعات والأندية، وافتح ملف أي لاعب أو حارس لرؤية مجاميع الموسم.", "Jelajahi tempat lahir di 32 tim, bandingkan konferensi dan klub, lalu buka pemain lapangan atau penjaga gawang untuk total musim."],
    ["Includes every player with at least one 2025–26 regular-season appearance. Birthplace is not nationality or where a player developed.", "Incluye a quienes jugaron al menos una vez en la temporada regular 2025–26. Nacimiento no equivale a nacionalidad ni lugar de formación.", "Inclut tout joueur ayant participé à la saison régulière 2025–26. Naissance ne signifie ni nationalité ni lieu de formation.", "يشمل كل لاعب شارك مرة واحدة على الأقل في الموسم العادي 2025–26. مكان الميلاد ليس الجنسية أو مكان تطور اللاعب.", "Mencakup semua pemain dengan setidaknya satu penampilan musim reguler 2025–26. Tempat lahir bukan kewarganegaraan atau tempat pemain berkembang."],
    ["Official NHL player birth-city fields matched conservatively to GeoNames coordinates.", "Las ciudades de nacimiento oficiales NHL se vinculan con cautela a coordenadas GeoNames.", "Les villes de naissance officielles NHL sont associées prudemment aux coordonnées GeoNames.", "طُوبقت حقول مدن الميلاد الرسمية للاعبي NHL بتحفظ مع إحداثيات GeoNames.", "Kolom kota lahir resmi pemain NHL dicocokkan secara hati-hati dengan koordinat GeoNames."],
    ["Club totals and recorded birthplaces come from the NHL public API. Coordinates come from GeoNames; local population estimates come from WorldPop.", "Los totales y nacimientos proceden de la API pública NHL. Las coordenadas vienen de GeoNames y la población local de WorldPop.", "Les totaux et naissances viennent de l’API publique NHL. Les coordonnées viennent de GeoNames et les populations locales de WorldPop.", "تأتي مجاميع الأندية وأماكن الميلاد المسجلة من واجهة NHL العامة، والإحداثيات من GeoNames، وتقديرات السكان المحليين من WorldPop.", "Total klub dan tempat lahir tercatat berasal dari API publik NHL. Koordinat dari GeoNames; perkiraan penduduk lokal dari WorldPop."],
    ["Explore verified birthplaces behind all 17 clubs, compare teams, and open any player for their season totals.", "Explora los nacimientos verificados de los 17 clubes, compara equipos y consulta los totales de cada jugador.", "Explorez les naissances vérifiées des 17 clubs, comparez les équipes et consultez les totaux de chaque joueur.", "استكشف أماكن ميلاد لاعبي الأندية الـ17 الموثّقة، وقارن الفرق، وافتح ملف أي لاعب لمجاميع موسمه.", "Jelajahi tempat lahir terverifikasi di 17 klub, bandingkan tim, dan buka pemain untuk melihat total musimnya."],
    ["Includes every player with a recorded 2025 regular-season appearance. Birthplace is not nationality or development pathway.", "Incluye a quienes tienen una aparición registrada en la temporada regular 2025. Nacimiento no equivale a nacionalidad ni trayectoria formativa.", "Inclut tout joueur ayant participé à la saison régulière 2025. Naissance ne signifie ni nationalité ni parcours de formation.", "يشمل كل لاعب سُجلت له مشاركة في موسم 2025 العادي. مكان الميلاد ليس الجنسية أو مسار التطور.", "Mencakup semua pemain dengan penampilan tercatat pada musim reguler 2025. Tempat lahir bukan kewarganegaraan atau jalur pengembangan."],
    ["Exact player names are matched only to Wikidata identities explicitly classified as rugby league players.", "Los nombres exactos se vinculan solo a identidades de Wikidata clasificadas expresamente como jugadores de rugby league.", "Les noms exacts ne sont associés qu’aux identités Wikidata clairement classées comme joueurs de rugby à XIII.", "تُطابق أسماء اللاعبين الدقيقة فقط مع هويات Wikidata المصنفة صراحةً كلاعبين في دوري الرغبي.", "Nama pemain yang persis dicocokkan hanya dengan identitas Wikidata yang secara tegas diklasifikasikan sebagai pemain rugby league."],
    ["Player-game totals come from Champion Data's 2025 NRL Match Centre feed. Birthplaces and coordinates come from Wikidata rugby-league identities; population estimates come from WorldPop.", "Los partidos proceden de Champion Data NRL Match Centre 2025. Nacimientos y coordenadas vienen de Wikidata; la población, de WorldPop.", "Les matchs viennent du flux Champion Data NRL Match Centre 2025. Naissances et coordonnées viennent de Wikidata ; les populations, de WorldPop.", "تأتي مباريات اللاعبين من بيانات Champion Data لمركز مباريات NRL 2025. وتأتي أماكن الميلاد وإحداثياتها من هويات Wikidata للرغبي، وتقديرات السكان من WorldPop.", "Total pertandingan pemain berasal dari umpan Champion Data NRL Match Centre 2025. Tempat lahir dan koordinat dari identitas rugby league Wikidata; perkiraan penduduk dari WorldPop."],
  ]);

  rows.push(...[
    ["Explore where the 620 fighters who competed in UFC events during 2025 were born—or, when birthplace is unavailable, their separately labelled official UFC hometown.", "Descubre dónde nacieron los 620 luchadores que compitieron en UFC en 2025 o, si falta el dato, su ciudad de origen oficial indicada por separado.", "Découvrez où sont nés les 620 combattants de l’UFC en 2025 ou, à défaut, leur ville d’origine officielle indiquée séparément.", "اكتشف أماكن ميلاد المقاتلين الـ620 الذين شاركوا في فعاليات UFC خلال 2025، أو مسقط رأسهم الرسمي المبيّن على نحو منفصل عند غياب الميلاد.", "Jelajahi tempat lahir 620 petarung yang bertanding di acara UFC selama 2025, atau kota asal resmi mereka yang diberi label terpisah bila tempat lahir tidak tersedia."],
    ["Red markers are verified birthplaces. Blue markers are official UFC fighter origins. Population maps use birthplaces only.", "Los marcadores rojos son nacimientos verificados; los azules, orígenes oficiales UFC. Los mapas de población usan solo nacimientos.", "Les marqueurs rouges sont des naissances vérifiées ; les bleus, des origines officielles UFC. Les cartes par population n’utilisent que les naissances.", "العلامات الحمراء لأماكن الميلاد الموثّقة، والزرقاء للأصول الرسمية لمقاتلي UFC. تستخدم خرائط السكان أماكن الميلاد فقط.", "Penanda merah adalah tempat lahir terverifikasi. Penanda biru adalah asal resmi petarung UFC. Peta penduduk hanya memakai tempat lahir."],
    ["Result cards supply the complete cohort. UFCStats supplies detailed round totals for 515 of 520 fights. Verified birthplaces take priority; official UFC hometown is a labelled fallback.", "Las tarjetas de resultados definen el grupo completo. UFCStats aporta detalles por asalto en 515 de 520 peleas. Se prioriza el nacimiento verificado; la ciudad de origen oficial UFC es alternativa señalada.", "Les résultats définissent la cohorte complète. UFCStats fournit les détails des rounds pour 515 combats sur 520. Les naissances vérifiées priment ; la ville d’origine officielle UFC sert de repli indiqué.", "تحدد بطاقات النتائج المجموعة الكاملة. يوفر UFCStats تفاصيل الجولات لـ515 من أصل 520 نزالًا. تُقدّم أماكن الميلاد الموثّقة؛ ويُستخدم مسقط الرأس الرسمي بديلًا معنونًا.", "Kartu hasil menentukan seluruh kelompok. UFCStats menyediakan rincian ronde untuk 515 dari 520 pertarungan. Tempat lahir terverifikasi diutamakan; kota asal resmi UFC menjadi cadangan berlabel."],
    ["Explore the verified birthplaces behind every player who entered the court in the completed 2025 women's and men's Volleyball Nations League.", "Explora los nacimientos verificados de todos los jugadores que pisaron la pista en la Liga de Naciones de Voleibol 2025 femenina y masculina.", "Explorez les naissances vérifiées de tous les joueurs entrés sur le terrain lors des Ligues des nations de volley-ball féminine et masculine 2025.", "استكشف أماكن الميلاد الموثّقة لكل لاعب دخل الملعب في دوري الأمم للكرة الطائرة للنساء والرجال لعام 2025 المكتمل.", "Jelajahi tempat lahir terverifikasi setiap pemain yang masuk lapangan dalam Volleyball Nations League putri dan putra 2025 yang telah selesai."],
    ["Official match centres cover all 116 women's and 116 men's matches, including the Finals. Set lineups, substitutions and libero appearances determine participation.", "Los centros oficiales cubren los 116 partidos femeninos y los 116 masculinos, incluidas las finales. Alineaciones por set, cambios y apariciones del líbero determinan la participación.", "Les feuilles officielles couvrent les 116 matchs féminins et 116 masculins, finales comprises. Compositions, remplacements et entrées des libéros déterminent la participation.", "تغطي سجلات المباريات الرسمية جميع مباريات النساء الـ116 والرجال الـ116، بما فيها النهائيات. تحدد تشكيلات الأشواط والتبديلات ومشاركات الليبرو المشاركة.", "Pusat pertandingan resmi mencakup 116 laga putri dan 116 putra, termasuk Final. Susunan set, pergantian, dan penampilan libero menentukan partisipasi."],
    ["Sets played and matches entered are compared consistently across both competitions. Scoring profiles separate attacks, blocks and aces.", "Sets y partidos se comparan igual en ambas competiciones. Los perfiles de puntos separan ataques, bloqueos y saques directos.", "Sets et matchs sont comparés de façon cohérente entre les deux compétitions. Les profils de points distinguent attaques, contres et aces.", "تُقارن الأشواط والمباريات بصورة متسقة بين البطولتين. وتفصل ملفات النقاط بين الهجمات والصد والإرسالات الساحقة.", "Set dan pertandingan dibandingkan secara konsisten di kedua kompetisi. Profil skor memisahkan serangan, blok, dan ace."],
    ["Stats: AFL Tables via fitzRoy · Geography: Wikidata + Wikipedia · Population: verified birthplaces only", "Estadísticas: AFL Tables vía fitzRoy · Geografía: Wikidata + Wikipedia · Población: solo nacimientos verificados", "Stats : AFL Tables via fitzRoy · Géographie : Wikidata + Wikipédia · Population : naissances vérifiées seulement", "الإحصاءات: AFL Tables عبر fitzRoy · الجغرافيا: Wikidata وWikipedia · السكان: أماكن الميلاد الموثّقة فقط", "Statistik: AFL Tables melalui fitzRoy · Geografi: Wikidata + Wikipedia · Penduduk: hanya tempat lahir terverifikasi"],
    ["Results: Official MotoGP & WorldWCR · Locations: official profiles, Wikidata & GeoNames", "Resultados: MotoGP y WorldWCR oficiales · Lugares: perfiles oficiales, Wikidata y GeoNames", "Résultats : MotoGP et WorldWCR officiels · Lieux : profils officiels, Wikidata et GeoNames", "النتائج: MotoGP وWorldWCR الرسميتان · المواقع: الملفات الرسمية وWikidata وGeoNames", "Hasil: MotoGP & WorldWCR resmi · Lokasi: profil resmi, Wikidata & GeoNames"],
  ]);

  rows.push(...[
    ["Accept coordinates only after country and province checks.", "Aceptar coordenadas solo tras comprobar país y provincia.", "N’accepter les coordonnées qu’après vérification du pays et de la province.", "لا تُقبل الإحداثيات إلا بعد التحقق من البلد والمقاطعة.", "Terima koordinat hanya setelah memeriksa negara dan provinsi."],
    ["Accept coordinates only after country and state checks.", "Aceptar coordenadas solo tras comprobar país y estado.", "N’accepter les coordonnées qu’après vérification du pays et de l’État.", "لا تُقبل الإحداثيات إلا بعد التحقق من البلد والولاية.", "Terima koordinat hanya setelah memeriksa negara dan negara bagian."],
    ["Assign half of each pair’s points to each partner.", "Asignar la mitad de los puntos de cada pareja a cada integrante.", "Attribuer la moitié des points de chaque paire à chaque partenaire.", "خصص نصف نقاط كل زوج لكل شريك.", "Bagikan separuh poin tiap pasangan kepada masing-masing anggota."],
    ["Combine plate appearances and batters faced as cross-position workload.", "Combinar apariciones al bate y bateadores enfrentados como actividad común entre posiciones.", "Combiner passages au bâton et frappeurs affrontés comme mesure commune entre postes.", "اجمع مرات الضرب والضاربين المواجَهين مقياسًا للمشاركة بين المراكز.", "Gabungkan giliran memukul dan pemukul yang dihadapi sebagai ukuran aktivitas lintas posisi."],
    ["Count combined events once, not once per discipline.", "Contar las pruebas combinadas una vez, no una vez por disciplina.", "Compter les épreuves combinées une fois, pas une fois par discipline.", "احسب الفعاليات المركبة مرة واحدة لا مرة لكل تخصص.", "Hitung nomor gabungan sekali, bukan sekali per disiplin."],
    ["Count each fighter once per completed bout.", "Contar cada luchador una vez por combate terminado.", "Compter chaque combattant une fois par combat terminé.", "احسب كل مقاتل مرة لكل نزال مكتمل.", "Hitung setiap petarung sekali per duel yang selesai."],
    ["Count every classified starter, including retirements.", "Contar a todos los participantes clasificados, incluidos los abandonos.", "Compter tous les partants classés, abandons compris.", "احسب كل من بدأ السباق وصُنّف، بمن فيهم المنسحبون.", "Hitung setiap pembalap yang tercatat start, termasuk yang gagal finis."],
    ["Count players only when they enter the court in a set.", "Contar jugadores solo cuando entran en pista durante un set.", "Compter les joueurs seulement lorsqu’ils entrent sur le terrain dans un set.", "احسب اللاعبين فقط عند دخولهم الملعب في شوط.", "Hitung pemain hanya saat mereka masuk lapangan dalam suatu set."],
    ["Deduplicate heats, semifinals and finals into one event entry.", "Unificar series, semifinales y finales en una sola inscripción por prueba.", "Regrouper séries, demi-finales et finales en une seule participation par épreuve.", "أزل تكرار التصفيات ونصف النهائيات والنهائيات في مشاركة واحدة لكل فعالية.", "Gabungkan babak penyisihan, semifinal, dan final menjadi satu keikutsertaan nomor."],
    ["Exclude super overs from performance totals.", "Excluir los super overs de los totales de rendimiento.", "Exclure les super overs des totaux de performance.", "استبعد الأشواط الإضافية من مجاميع الأداء.", "Kecualikan super over dari total performa."],
    ["Freeze the final 2025 FIP ranking cohort.", "Fijar el grupo de la clasificación FIP final de 2025.", "Figer la cohorte du classement FIP final 2025.", "ثبّت مجموعة تصنيف FIP النهائي لعام 2025.", "Tetapkan kelompok peringkat akhir FIP 2025."],
    ["Freeze the official ATP and WTA year-end lists.", "Fijar las listas oficiales ATP y WTA de fin de año.", "Figer les listes officielles ATP et WTA de fin d’année.", "ثبّت قوائم ATP وWTA الرسمية لنهاية العام.", "Tetapkan daftar resmi akhir tahun ATP dan WTA."],
    ["Join detailed statistics where available.", "Añadir estadísticas detalladas cuando existan.", "Joindre les statistiques détaillées lorsqu’elles existent.", "أضف الإحصاءات التفصيلية حيث تتوفر.", "Gabungkan statistik rinci bila tersedia."],
    ["Keep 100 singles players and 50 pairs per doubles event.", "Conservar 100 individuales y 50 parejas por modalidad de dobles.", "Garder 100 joueurs en simple et 50 paires par épreuve de double.", "احتفظ بـ100 لاعب فردي و50 زوجًا لكل فعالية زوجية.", "Pertahankan 100 pemain tunggal dan 50 pasangan per nomor ganda."],
    ["Keep all completed preliminary and finals matches.", "Conservar todos los partidos preliminares y finales terminados.", "Garder tous les matchs préliminaires et finaux terminés.", "احتفظ بجميع المباريات التمهيدية والنهائية المكتملة.", "Pertahankan semua pertandingan penyisihan dan final yang selesai."],
    ["Keep anyone with at least one logged snap.", "Conservar a quien tenga al menos una jugada registrada.", "Garder toute personne ayant au moins une action enregistrée.", "أبقِ كل من سُجلت له لعبة واحدة على الأقل.", "Pertahankan siapa pun dengan setidaknya satu snap tercatat."],
    ["Keep athletes with an official result other than DNS.", "Conservar atletas con resultado oficial distinto de DNS.", "Garder les athlètes ayant un résultat officiel autre que DNS.", "أبقِ الرياضيين ذوي النتائج الرسمية باستثناء من لم يبدأوا.", "Pertahankan atlet dengan hasil resmi selain tidak mulai."],
    ["Keep calendar-year 2025 T20 internationals.", "Conservar los T20 internacionales del año natural 2025.", "Garder les T20 internationaux de l’année civile 2025.", "احتفظ بمباريات T20 الدولية للسنة التقويمية 2025.", "Pertahankan T20 internasional sepanjang tahun kalender 2025."],
    ["Keep championship races and sprints only.", "Conservar solo carreras y sprints del campeonato.", "Garder seulement les courses et sprints de championnat.", "احتفظ بسباقات البطولة والسباقات القصيرة فقط.", "Pertahankan hanya balapan dan sprint kejuaraan."],
    ["Keep every missing coordinate visible for QA.", "Mantener visibles las coordenadas faltantes para revisión.", "Garder les coordonnées manquantes visibles pour vérification.", "أبقِ كل إحداثية مفقودة ظاهرة للمراجعة.", "Tampilkan setiap koordinat yang hilang untuk pemeriksaan."],
    ["Keep exact per-team splits for traded players.", "Conservar los datos exactos por equipo de los jugadores transferidos.", "Garder les répartitions exactes par équipe des joueurs transférés.", "احتفظ بتقسيمات دقيقة حسب الفريق للاعبين المنتقلين.", "Pertahankan rincian tepat per tim untuk pemain yang pindah."],
    ["Keep exact team splits for traded players.", "Conservar los datos exactos por equipo de los jugadores transferidos.", "Garder les répartitions exactes par équipe des joueurs transférés.", "احتفظ بتقسيمات دقيقة حسب الفريق للاعبين المنتقلين.", "Pertahankan rincian tepat per tim untuk pemain yang pindah."],
    ["Preserve raw points within each ranking system.", "Conservar los puntos originales de cada sistema de clasificación.", "Préserver les points bruts de chaque système de classement.", "احتفظ بالنقاط الخام داخل كل نظام تصنيف.", "Pertahankan poin asli dalam setiap sistem peringkat."],
    ["Preserve team and series splits for movers.", "Conservar el desglose por equipo y categoría de quienes cambiaron.", "Préserver les répartitions par équipe et série des pilotes ayant changé.", "احتفظ بتقسيمات الفريق والفئة لمن انتقلوا.", "Pertahankan rincian tim dan seri untuk yang berpindah."],
    ["Preserve women's and men's competition splits.", "Conservar por separado las competiciones femeninas y masculinas.", "Préserver les répartitions entre compétitions féminines et masculines.", "احتفظ بفصل منافسات النساء والرجال.", "Pertahankan rincian kompetisi putri dan putra."],
    ["Read the recorded birth city, province and country.", "Leer la ciudad, provincia y país de nacimiento registrados.", "Lire la ville, province et pays de naissance enregistrés.", "اقرأ مدينة الميلاد والمقاطعة والبلد المسجلة.", "Baca kota, provinsi, dan negara kelahiran yang tercatat."],
    ["Resolve the recorded birthplace and coordinates.", "Determinar el nacimiento registrado y sus coordenadas.", "Déterminer le lieu de naissance enregistré et ses coordonnées.", "حدد مكان الميلاد المسجل وإحداثياته.", "Tentukan tempat lahir tercatat dan koordinatnya."],
    ["Select players representing ICC Full Member teams.", "Seleccionar jugadores de selecciones miembro pleno de la ICC.", "Sélectionner les joueurs des équipes membres de plein droit de l’ICC.", "اختر لاعبي فرق الأعضاء الكاملين في ICC.", "Pilih pemain yang mewakili tim anggota penuh ICC."],
    ["Start with every player in official 2025 team hitting and pitching summaries.", "Partir de todos los jugadores en los resúmenes oficiales de bateo y lanzamiento de 2025.", "Partir de tous les joueurs des bilans officiels 2025 de frappe et de lancer.", "ابدأ بكل لاعب في ملخصات الضرب والرمي الرسمية لفرق 2025.", "Mulai dari semua pemain dalam ringkasan resmi memukul dan melempar tim 2025."],
    ["Start with every player recorded by the NBA Stats API.", "Partir de todos los jugadores registrados por NBA Stats API.", "Partir de tous les joueurs recensés par l’API NBA Stats.", "ابدأ بكل لاعب سجلته واجهة NBA Stats.", "Mulai dari semua pemain yang tercatat dalam NBA Stats API."],
    ["Start with every skater and goalie in official club summaries.", "Partir de todos los jugadores y porteros de los resúmenes oficiales de clubes.", "Partir de tous les patineurs et gardiens des bilans officiels des clubs.", "ابدأ بكل لاعب وحارس في ملخصات الأندية الرسمية.", "Mulai dari semua pemain lapangan dan penjaga gawang dalam ringkasan resmi klub."],
    ["Start with regular-season snap counts from nflverse.", "Partir de las jugadas de temporada regular de nflverse.", "Partir des nombres d’actions de saison régulière de nflverse.", "ابدأ بعدد اللعبات في الموسم العادي من nflverse.", "Mulai dari jumlah snap musim reguler dari nflverse."],
    ["Use aggregate player rows and remove unused reserves.", "Usar filas agregadas y eliminar reservas no utilizadas.", "Utiliser les lignes agrégées et retirer les remplaçants non utilisés.", "استخدم صفوف اللاعبين المجمعة وأزل الاحتياطيين غير المشاركين.", "Gunakan baris pemain agregat dan hapus cadangan yang tidak dimainkan."],
    ["Use birthplace first, then labelled original team; publish misses to QA.", "Priorizar nacimiento y después equipo original señalado; enviar faltantes a revisión.", "Privilégier la naissance puis l’équipe d’origine indiquée ; soumettre les manques à vérification.", "قدّم مكان الميلاد ثم الفريق الأصلي المعنون؛ وأحِل النواقص للمراجعة.", "Utamakan tempat lahir lalu tim asal berlabel; kirim yang hilang untuk pemeriksaan."],
    ["Verify identities with exact dates of birth.", "Verificar identidades mediante fechas de nacimiento exactas.", "Vérifier les identités avec les dates de naissance exactes.", "تحقق من الهويات بتواريخ الميلاد الدقيقة.", "Verifikasi identitas dengan tanggal lahir yang tepat."],
  ]);

  rows.push(...[
    ["Allocated year-end ranking points connected to a verified birthplace coordinate.", "Puntos de clasificación final vinculados a coordenadas de nacimiento verificadas.", "Points de classement final liés à des coordonnées de naissance vérifiées.", "نقاط تصنيف نهاية العام المرتبطة بإحداثيات مكان ميلاد موثّقة.", "Poin peringkat akhir tahun yang terkait dengan koordinat tempat lahir terverifikasi."],
    ["Completed racing laps attached to a verified driver birthplace.", "Vueltas completadas vinculadas al nacimiento verificado de un piloto.", "Tours de course terminés liés à la naissance vérifiée d’un pilote.", "اللفات المكتملة المرتبطة بمكان ميلاد سائق موثّق.", "Putaran balap selesai yang terkait dengan tempat lahir pembalap terverifikasi."],
    ["Completed racing laps attached to a verified rider birthplace.", "Vueltas completadas vinculadas al nacimiento verificado de un piloto.", "Tours de course terminés liés à la naissance vérifiée d’un pilote.", "اللفات المكتملة المرتبطة بمكان ميلاد متسابق موثّق.", "Putaran balap selesai yang terkait dengan tempat lahir pembalap terverifikasi."],
    ["Event entries by athletes with a verified birthplace.", "Inscripciones de atletas con nacimiento verificado.", "Participations d’athlètes dont la naissance est vérifiée.", "مشاركات الرياضيين ذوي أماكن الميلاد الموثّقة.", "Keikutsertaan atlet dengan tempat lahir terverifikasi."],
    ["Fighter-bout appearances attached to a known location.", "Participaciones en combates vinculadas a una ubicación conocida.", "Participations aux combats liées à un lieu connu.", "مشاركات المقاتلين في النزالات المرتبطة بموقع معروف.", "Penampilan petarung dalam duel yang terkait dengan lokasi diketahui."],
    ["Final ranking points connected to a verified birthplace coordinate.", "Puntos de clasificación final vinculados a coordenadas de nacimiento verificadas.", "Points de classement final liés à des coordonnées de naissance vérifiées.", "نقاط التصنيف النهائي المرتبطة بإحداثيات مكان ميلاد موثّقة.", "Poin peringkat akhir yang terkait dengan koordinat tempat lahir terverifikasi."],
    ["Plate appearances and batters faced connected to a validated birthplace.", "Turnos de bateo y bateadores enfrentados vinculados a un nacimiento validado.", "Passages au bâton et frappeurs affrontés liés à une naissance validée.", "مرات الضرب والضاربون المواجَهون المرتبطون بمكان ميلاد موثّق.", "Giliran memukul dan pemukul yang dihadapi terkait dengan tempat lahir tervalidasi."],
    ["Player appearances connected to a verified birthplace coordinate.", "Participaciones vinculadas a coordenadas de nacimiento verificadas.", "Apparitions de joueurs liées à des coordonnées de naissance vérifiées.", "مشاركات اللاعبين المرتبطة بإحداثيات مكان ميلاد موثّقة.", "Penampilan pemain yang terkait dengan koordinat tempat lahir terverifikasi."],
    ["Player-games connected to a verified birthplace coordinate.", "Partidos de jugadores vinculados a coordenadas de nacimiento verificadas.", "Matchs de joueurs liés à des coordonnées de naissance vérifiées.", "مباريات اللاعبين المرتبطة بإحداثيات مكان ميلاد موثّقة.", "Pertandingan pemain yang terkait dengan koordinat tempat lahir terverifikasi."],
    ["Players connected to an ESPN birth city and a matching GeoNames coordinate.", "Jugadores vinculados a ciudad de nacimiento ESPN y coordenada GeoNames coincidente.", "Joueurs liés à une ville de naissance ESPN et à une coordonnée GeoNames correspondante.", "لاعبون مرتبطون بمدينة ميلاد من ESPN وإحداثيات مطابقة من GeoNames.", "Pemain yang terkait dengan kota lahir ESPN dan koordinat GeoNames yang cocok."],
    ["Players linked to an exact-DOB-verified Wikidata birthplace with coordinates.", "Jugadores vinculados a nacimiento Wikidata con fecha exacta verificada y coordenadas.", "Joueurs liés à une naissance Wikidata avec date exacte vérifiée et coordonnées.", "لاعبون مرتبطون بمكان ميلاد من Wikidata تحقّق تاريخه الدقيق وإحداثياته.", "Pemain yang terhubung ke tempat lahir Wikidata dengan tanggal lahir tepat dan koordinat terverifikasi."],
    ["Regular-season minutes connected to a validated birthplace.", "Minutos de temporada regular vinculados a un nacimiento validado.", "Minutes de saison régulière liées à une naissance validée.", "دقائق الموسم العادي المرتبطة بمكان ميلاد موثّق.", "Menit musim reguler yang terkait dengan tempat lahir tervalidasi."],
    ["Regular-season player-minutes connected to a validated birthplace.", "Minutos de jugadores en temporada regular vinculados a un nacimiento validado.", "Minutes de joueurs en saison régulière liées à une naissance validée.", "دقائق اللاعبين في الموسم العادي المرتبطة بمكان ميلاد موثّق.", "Menit pemain musim reguler yang terkait dengan tempat lahir tervalidasi."],
    ["Regular-season snaps connected to a validated birthplace coordinate.", "Jugadas de temporada regular vinculadas a coordenadas de nacimiento validadas.", "Actions de saison régulière liées à des coordonnées de naissance validées.", "لعبات الموسم العادي المرتبطة بإحداثيات مكان ميلاد موثّقة.", "Snap musim reguler yang terkait dengan koordinat tempat lahir tervalidasi."],
    ["Riders linked to an official birthplace with verified coordinates.", "Pilotos vinculados a nacimiento oficial con coordenadas verificadas.", "Pilotes liés à une naissance officielle avec coordonnées vérifiées.", "متسابقون مرتبطون بمكان ميلاد رسمي ذي إحداثيات موثّقة.", "Pembalap yang terkait dengan tempat lahir resmi berkoordinat terverifikasi."],
    ["Sets played by players with a verified birthplace.", "Sets jugados por jugadores con nacimiento verificado.", "Sets joués par des joueurs dont la naissance est vérifiée.", "الأشواط التي لعبها لاعبون ذوو أماكن ميلاد موثّقة.", "Set yang dimainkan pemain dengan tempat lahir terverifikasi."],
    ["Year-end FIP ranking points connected to a verified birthplace coordinate.", "Puntos FIP finales vinculados a coordenadas de nacimiento verificadas.", "Points FIP de fin d’année liés à des coordonnées de naissance vérifiées.", "نقاط FIP لنهاية العام المرتبطة بإحداثيات مكان ميلاد موثّقة.", "Poin peringkat FIP akhir tahun yang terkait dengan koordinat tempat lahir terverifikasi."],
    ["Year-end ranking points connected to a verified birthplace coordinate.", "Puntos finales vinculados a coordenadas de nacimiento verificadas.", "Points de classement de fin d’année liés à des coordonnées de naissance vérifiées.", "نقاط تصنيف نهاية العام المرتبطة بإحداثيات مكان ميلاد موثّقة.", "Poin peringkat akhir tahun yang terkait dengan koordinat tempat lahir terverifikasi."],
    ["Drivers linked to a verified Wikidata birthplace with coordinates.", "Pilotos vinculados a nacimiento Wikidata verificado con coordenadas.", "Pilotes liés à une naissance Wikidata vérifiée avec coordonnées.", "سائقون مرتبطون بمكان ميلاد موثّق في Wikidata مع إحداثيات.", "Pembalap yang terkait dengan tempat lahir Wikidata berkoordinat terverifikasi."],
    ["World Athletics IDs link athletes to coordinate-bearing Wikidata birthplaces.", "Los IDs de World Athletics vinculan atletas con nacimientos Wikidata con coordenadas.", "Les identifiants World Athletics relient les athlètes aux naissances Wikidata géolocalisées.", "تربط معرّفات World Athletics الرياضيين بأماكن ميلاد في Wikidata ذات إحداثيات.", "ID World Athletics menghubungkan atlet dengan tempat lahir Wikidata yang memiliki koordinat."],
    ["Official MLB birth-city fields matched conservatively to GeoNames coordinates.", "Ciudades de nacimiento oficiales MLB vinculadas con cautela a coordenadas GeoNames.", "Villes de naissance officielles MLB associées prudemment aux coordonnées GeoNames.", "طُوبقت حقول مدن الميلاد الرسمية في MLB بتحفظ مع إحداثيات GeoNames.", "Kolom kota lahir resmi MLB dicocokkan secara hati-hati dengan koordinat GeoNames."],
    ["Verified birthplaces plus separately labelled official UFC hometowns.", "Nacimientos verificados más ciudades oficiales UFC señaladas por separado.", "Naissances vérifiées et villes d’origine officielles UFC indiquées séparément.", "أماكن ميلاد موثّقة مع مساقط رأس UFC الرسمية المعنونة منفصلًا.", "Tempat lahir terverifikasi beserta kota asal resmi UFC yang diberi label terpisah."],
    ["Birthplace and origin are never conflated", "Nacimiento y origen nunca se confunden", "Naissance et origine ne sont jamais confondues", "لا يُخلط مكان الميلاد بالأصل", "Tempat lahir dan asal tidak pernah disamakan"],
    ["No association-to-birthplace substitution", "La federación no sustituye el nacimiento", "La fédération ne remplace pas la naissance", "لا تُستخدم الرابطة بدل مكان الميلاد", "Asosiasi tidak menggantikan tempat lahir"],
    ["Fighters may appear in multiple divisions", "Un luchador puede aparecer en varias divisiones", "Un combattant peut figurer dans plusieurs divisions", "قد يظهر المقاتل في أكثر من فئة", "Petarung dapat muncul di beberapa divisi"],
    ["Schedules differ between men's and women's cricket", "Los calendarios difieren entre críquet masculino y femenino", "Les calendriers diffèrent entre cricket masculin et féminin", "تختلف الجداول بين كريكيت الرجال والنساء", "Jadwal kriket putra dan putri berbeda"],
    ["Women's and men's competitions are equally weighted", "Las competiciones femeninas y masculinas tienen el mismo peso", "Les compétitions féminines et masculines ont le même poids", "تُوزن منافسات النساء والرجال بالتساوي", "Kompetisi putri dan putra diberi bobot sama"],
    ["Who plays—and where verified birthplaces lie", "Quién juega y dónde están los nacimientos verificados", "Qui joue et où se trouvent les naissances vérifiées", "من يلعب وأين تقع أماكن الميلاد الموثّقة", "Siapa yang bermain dan di mana tempat lahir terverifikasi berada"],
  ]);

  rows.push(...[
    ["ATP and WTA players matching the current filters", "Jugadores ATP y WTA que coinciden con los filtros", "Joueurs ATP et WTA correspondant aux filtres", "لاعبو ATP وWTA المطابقون للمرشحات", "Pemain ATP dan WTA yang sesuai filter"],
    ["Badminton athletes matching the current filters", "Atletas de bádminton que coinciden con los filtros", "Athlètes de badminton correspondant aux filtres", "رياضيّو الريشة الطائرة المطابقون للمرشحات", "Atlet bulu tangkis yang sesuai filter"],
    ["Cricket players matching the current filters", "Jugadores de críquet que coinciden con los filtros", "Joueurs de cricket correspondant aux filtres", "لاعبو الكريكيت المطابقون للمرشحات", "Pemain kriket yang sesuai filter"],
    ["FIP men and women players matching the current filters", "Jugadores y jugadoras FIP que coinciden con los filtros", "Joueurs et joueuses FIP correspondant aux filtres", "لاعبو ولاعبات FIP المطابقون للمرشحات", "Pemain putra dan putri FIP yang sesuai filter"],
    ["Interactive map of AFL player birthplaces and football origins", "Mapa interactivo de nacimientos y orígenes futbolísticos AFL", "Carte interactive des naissances et origines footballistiques AFL", "خريطة تفاعلية لأماكن ميلاد لاعبي AFL وأصولهم الكروية", "Peta interaktif tempat lahir dan asal sepak bola pemain AFL"],
    ["Interactive map of ATP and WTA player birthplaces", "Mapa interactivo de nacimientos ATP y WTA", "Carte interactive des naissances des joueurs ATP et WTA", "خريطة تفاعلية لأماكن ميلاد لاعبي ATP وWTA", "Peta interaktif tempat lahir pemain ATP dan WTA"],
    ["Interactive map of FIP men and women player birthplaces", "Mapa interactivo de nacimientos FIP masculinos y femeninos", "Carte interactive des naissances des joueurs FIP hommes et femmes", "خريطة تفاعلية لأماكن ميلاد لاعبي ولاعبات FIP", "Peta interaktif tempat lahir pemain putra dan putri FIP"],
    ["Interactive map of MLB player birthplaces", "Mapa interactivo de nacimientos MLB", "Carte interactive des naissances des joueurs MLB", "خريطة تفاعلية لأماكن ميلاد لاعبي MLB", "Peta interaktif tempat lahir pemain MLB"],
    ["Interactive map of NBA player birthplaces", "Mapa interactivo de nacimientos NBA", "Carte interactive des naissances des joueurs NBA", "خريطة تفاعلية لأماكن ميلاد لاعبي NBA", "Peta interaktif tempat lahir pemain NBA"],
    ["Interactive map of NFL player birthplaces", "Mapa interactivo de nacimientos NFL", "Carte interactive des naissances des joueurs NFL", "خريطة تفاعلية لأماكن ميلاد لاعبي NFL", "Peta interaktif tempat lahir pemain NFL"],
    ["Interactive map of NHL player birthplaces", "Mapa interactivo de nacimientos NHL", "Carte interactive des naissances des joueurs NHL", "خريطة تفاعلية لأماكن ميلاد لاعبي NHL", "Peta interaktif tempat lahir pemain NHL"],
    ["Interactive map of NRL player birthplaces", "Mapa interactivo de nacimientos NRL", "Carte interactive des naissances des joueurs NRL", "خريطة تفاعلية لأماكن ميلاد لاعبي NRL", "Peta interaktif tempat lahir pemain NRL"],
    ["Interactive map of international cricketer birthplaces", "Mapa interactivo de nacimientos de jugadores internacionales de críquet", "Carte interactive des naissances des joueurs de cricket internationaux", "خريطة تفاعلية لأماكن ميلاد لاعبي الكريكيت الدوليين", "Peta interaktif tempat lahir pemain kriket internasional"],
    ["Interactive map of ranked badminton athlete birthplaces", "Mapa interactivo de nacimientos de atletas de bádminton clasificados", "Carte interactive des naissances des athlètes de badminton classés", "خريطة تفاعلية لأماكن ميلاد رياضيي الريشة الطائرة المصنفين", "Peta interaktif tempat lahir atlet bulu tangkis berperingkat"],
    ["Interactive map of ranked golfer birthplaces", "Mapa interactivo de nacimientos de golfistas clasificados", "Carte interactive des naissances des golfeurs classés", "خريطة تفاعلية لأماكن ميلاد لاعبي الغولف المصنفين", "Peta interaktif tempat lahir pegolf berperingkat"],
  ]);

  rows.push(...[
    ["Filters", "Filtros", "Filtres", "المرشحات", "Filter"],
    ["Big Five European domestic leagues", "Cinco grandes ligas europeas", "Cinq grands championnats européens", "الدوريات الأوروبية الخمسة الكبرى", "Lima liga domestik utama Eropa"],
    ["Men’s and women’s Full Member T20 internationals", "T20 internacionales masculinos y femeninos de miembros plenos", "T20 internationaux féminins et masculins des membres à part entière", "مباريات T20 الدولية للرجال والنساء من الأعضاء الكاملين", "T20 internasional putra dan putri anggota penuh"],
    ["All 42 UFC events", "Los 42 eventos UFC", "Les 42 événements UFC", "جميع فعاليات UFC الـ42", "Seluruh 42 acara UFC"],
    ["F1, F2, F3 and F1 Academy", "F1, F2, F3 y F1 Academy", "F1, F2, F3 et F1 Academy", "فورمولا 1 و2 و3 وأكاديمية F1", "F1, F2, F3, dan F1 Academy"],
    ["MotoGP, Moto2, Moto3, MotoE and WorldWCR", "MotoGP, Moto2, Moto3, MotoE y WorldWCR", "MotoGP, Moto2, Moto3, MotoE et WorldWCR", "MotoGP وMoto2 وMoto3 وMotoE وWorldWCR", "MotoGP, Moto2, Moto3, MotoE, dan WorldWCR"],
    ["Women’s and men’s Volleyball Nations League", "Liga de Naciones de Voleibol femenina y masculina", "Ligues des nations de volleyball féminine et masculine", "دوري الأمم للكرة الطائرة للسيدات والرجال", "Volleyball Nations League putri dan putra"],
    ["World Athletics Championships · all 49 events", "Mundial de Atletismo · 49 pruebas", "Championnats du monde d’athlétisme · 49 épreuves", "بطولة العالم لألعاب القوى · جميع الفعاليات الـ49", "Kejuaraan Atletik Dunia · seluruh 49 nomor"],
    ["Year-end ATP and WTA singles top 100", "Top 100 individual ATP y WTA de fin de año", "Top 100 de simple ATP et WTA en fin d’année", "أفضل 100 لاعب فردي في ATP وWTA لنهاية العام", "100 besar tunggal ATP dan WTA akhir tahun"],
    ["Year-end FIP men’s and women’s top 100", "Top 100 FIP masculino y femenino de fin de año", "Top 100 FIP féminin et masculin en fin d’année", "أفضل 100 رجل وامرأة في FIP لنهاية العام", "100 besar FIP putra dan putri akhir tahun"],
    ["Top singles players and doubles pairs", "Mejores jugadores individuales y parejas de dobles", "Meilleurs joueurs en simple et paires de double", "أفضل اللاعبين الفرديين والأزواج", "Pemain tunggal dan pasangan ganda teratas"],
    ["Final men’s and women’s world top 100", "Top 100 mundial final masculino y femenino", "Top 100 mondial final féminin et masculin", "أفضل 100 عالميًا للرجال والنساء في التصنيف النهائي", "100 besar dunia akhir putra dan putri"],
    ["Men’s home-and-away season", "Temporada regular masculina", "Saison régulière masculine", "الموسم الاعتيادي للرجال", "Musim kandang dan tandang putra"],
    ["Men’s regular season", "Temporada regular masculina", "Saison régulière masculine", "الموسم الاعتيادي للرجال", "Musim reguler putra"],
    ["Athletes matching filters", "Atletas que coinciden con los filtros", "Athlètes correspondant aux filtres", "الرياضيون المطابقون للمرشحات", "Atlet yang sesuai filter"],
    ["Formula drivers matching filters", "Pilotos de fórmula que coinciden con los filtros", "Pilotes de formule correspondant aux filtres", "سائقو الفورمولا المطابقون للمرشحات", "Pembalap Formula yang sesuai filter"],
    ["Golfers matching the current filters", "Golfistas que coinciden con los filtros", "Golfeurs correspondant aux filtres", "لاعبو الغولف المطابقون للمرشحات", "Pegolf yang sesuai filter"],
    ["Motorcycle riders matching filters", "Pilotos de motociclismo que coinciden con los filtros", "Pilotes de moto correspondant aux filtres", "متسابقو الدراجات المطابقون للمرشحات", "Pembalap motor yang sesuai filter"],
    ["UFC fighters matching filters", "Luchadores UFC que coinciden con los filtros", "Combattants UFC correspondant aux filtres", "مقاتلو UFC المطابقون للمرشحات", "Petarung UFC yang sesuai filter"],
    ["Volleyball players matching filters", "Jugadores de voleibol que coinciden con los filtros", "Joueurs de volleyball correspondant aux filtres", "لاعبو الكرة الطائرة المطابقون للمرشحات", "Pemain voli yang sesuai filter"],
    ["Birthplace mix, age and allocated points", "Lugares de nacimiento, edades y puntos asignados", "Origines, âges et points attribués", "تنوع أماكن الميلاد والأعمار والنقاط المخصصة", "Sebaran tempat lahir, usia, dan poin dialokasikan"],
    ["Birthplace mix, player age and games", "Lugares de nacimiento, edades y partidos", "Origines, âges des joueurs et matchs", "تنوع أماكن الميلاد وأعمار اللاعبين والمباريات", "Sebaran tempat lahir, usia pemain, dan pertandingan"],
    ["Known-location mix, player age and games", "Lugares conocidos, edades y partidos", "Lieux connus, âges des joueurs et matchs", "تنوع المواقع المعروفة وأعمار اللاعبين والمباريات", "Sebaran lokasi diketahui, usia pemain, dan pertandingan"],
    ["Age & verified birthplace mix", "Edades y lugares de nacimiento verificados", "Âges et lieux de naissance vérifiés", "الأعمار وتنوع أماكن الميلاد الموثّقة", "Usia & sebaran tempat lahir terverifikasi"],
    ["Who competed—and where they were born", "Quién compitió y dónde nació", "Qui a concouru et où ces athlètes sont nés", "من تنافس وأين وُلد", "Siapa yang bertanding dan di mana mereka lahir"],
    ["Who fought—and where they came from", "Quién luchó y de dónde vino", "Qui a combattu et d’où venaient les combattants", "من قاتل ومن أين أتى", "Siapa yang bertarung dan dari mana asalnya"],
    ["Women and men on one map", "Mujeres y hombres en un mapa", "Femmes et hommes sur une même carte", "النساء والرجال على خريطة واحدة", "Putri dan putra dalam satu peta"],
    ["Women, men and mixed-only athletes", "Atletas femeninos, masculinos y solo mixtos", "Athlètes femmes, hommes et de mixte uniquement", "رياضيات ورياضيون ومشاركون في المختلط فقط", "Atlet putri, putra, dan khusus ganda campuran"],
    ["Two location standards", "Dos criterios de ubicación", "Deux normes de localisation", "معياران للموقع", "Dua standar lokasi"],
    ["No team-to-birthplace substitution", "Sin sustituir equipo por nacimiento", "Aucune substitution d’équipe au lieu de naissance", "لا يُستعاض عن مكان الميلاد بالفريق", "Tim tidak menggantikan tempat lahir"],
    ["Origins never enter population maps", "Los orígenes nunca entran en mapas de población", "Les origines n’entrent jamais dans les cartes de population", "لا تدخل الأصول خرائط السكان مطلقًا", "Asal tidak pernah masuk peta populasi"],
    ["Birthplace or labelled origin", "Nacimiento u origen identificado", "Naissance ou origine indiquée", "مكان الميلاد أو الأصل الموسوم", "Tempat lahir atau asal berlabel"],
    ["Birthplace or official origin", "Nacimiento u origen oficial", "Naissance ou origine officielle", "مكان الميلاد أو الأصل الرسمي", "Tempat lahir atau asal resmi"],
    ["College pathway", "Trayectoria universitaria", "Parcours universitaire", "المسار الجامعي", "Jalur perguruan tinggi"],
    ["College QA queue", "Pendientes universitarios de revisión", "Vérifications universitaires en attente", "طابور مراجعة الكليات", "Antrean pemeriksaan perguruan tinggi"],
    ["Comparable participation", "Participación comparable", "Participation comparable", "مشاركة قابلة للمقارنة", "Partisipasi sebanding"],
    ["Read comparisons carefully", "Lee las comparaciones con cuidado", "Lisez les comparaisons avec prudence", "اقرأ المقارنات بحذر", "Baca perbandingan dengan cermat"],
    ["Attack pts", "Puntos de ataque", "Points d’attaque", "نقاط الهجوم", "Poin serangan"],
    ["Block pts", "Puntos de bloqueo", "Points de contre", "نقاط الصد", "Poin blok"],
    ["Catches", "Recepciones", "Réceptions", "الالتقاطات", "Tangkapan"],
    ["Disposals", "Acciones con balón", "Possessions", "التصرفات بالكرة", "Penguasaan bola"],
    ["Home runs", "Jonrones", "Coups de circuit", "ضربات منزلية", "Home run"],
    ["Hits", "Hits", "Coups sûrs", "الضربات الناجحة", "Hit"],
    ["Wickets", "Wickets", "Guichets", "الويكيتات", "Wicket"],
    ["Runs", "Carreras", "Courses", "الأشواط", "Run"],
    ["Rebounds", "Rebotes", "Rebonds", "المتابعات", "Rebound"],
    ["Tackles", "Placajes", "Plaquages", "العرقلات", "Tekel"],
    ["Tries", "Ensayos", "Essais", "المحاولات", "Try"],
    ["Run metres", "Metros ganados", "Mètres parcourus", "أمتار الجري", "Meter lari"],
    ["Ice time", "Tiempo sobre hielo", "Temps de glace", "وقت اللعب على الجليد", "Waktu di es"],
    ["Height cm", "Altura cm", "Taille cm", "الطول سم", "Tinggi cm"],
    ["KO/TKO wins", "Victorias por KO/TKO", "Victoires par KO/TKO", "انتصارات بالضربة القاضية", "Kemenangan KO/TKO"],
    ["Submission wins", "Victorias por sumisión", "Victoires par soumission", "انتصارات بالإخضاع", "Kemenangan submission"],
    ["Sig. strikes", "Golpes significativos", "Coups significatifs", "الضربات المؤثرة", "Serangan signifikan"],
    ["Pitching K", "Ponches", "Retraits sur prises", "الإقصاءات بالرمي", "Strikeout pitching"],
    ["Player of match", "Jugador del partido", "Joueur du match", "أفضل لاعب في المباراة", "Pemain terbaik pertandingan"],
    ["Match method", "Método de partidos", "Méthode des matchs", "منهجية المباريات", "Metode pertandingan"],
    ["Fight method", "Método de combates", "Méthode des combats", "منهجية النزالات", "Metode duel"],
    ["Race method", "Método de carreras", "Méthode des courses", "منهجية السباقات", "Metode balapan"],
    ["Doubles method", "Método de dobles", "Méthode du double", "منهجية الزوجي", "Metode ganda"],
    ["Detailed", "Detallado", "Détaillé", "مفصل", "Rinci"],
    ["Championship", "Campeonato", "Championnat", "البطولة", "Kejuaraan"],
    ["Home-and-away", "Local y visitante", "Domicile et extérieur", "ذهابًا وإيابًا", "Kandang dan tandang"],
    ["Regular-season total", "Total de temporada regular", "Total de saison régulière", "إجمالي الموسم الاعتيادي", "Total musim reguler"],
    ["Regular-season minutes", "Minutos de temporada regular", "Minutes de saison régulière", "دقائق الموسم الاعتيادي", "Menit musim reguler"],
    ["Talent Geography home", "Inicio de Geografía del talento", "Accueil de Géographie du talent", "الصفحة الرئيسية لجغرافيا المواهب", "Beranda Geografi Talenta"],
    ["Where the world’s", "De dónde vienen los", "D’où viennent les", "من أين يأتي", "Dari mana asal"],
    ["Building the starting grid", "Preparando la parrilla de salida", "Préparation de la grille de départ", "جارٍ إعداد شبكة الانطلاق", "Menyiapkan grid start"],
    ["Setting the blocks", "Preparando la salida", "Préparation des blocs de départ", "جارٍ إعداد مضمار البداية", "Menyiapkan blok start"],
    ["Setting the court", "Preparando la pista", "Préparation du terrain", "جارٍ إعداد الملعب", "Menyiapkan lapangan"],
    ["Maps need athletes.", "Los mapas necesitan atletas.", "Les cartes ont besoin d’athlètes.", "تحتاج الخرائط إلى رياضيين.", "Peta membutuhkan atlet."],
    ["How doubles work", "Cómo funcionan los dobles", "Fonctionnement du double", "كيف يعمل الزوجي", "Cara kerja ganda"],
    ["Pairs stay pairs.", "Las parejas siguen siendo parejas.", "Les paires restent des paires.", "تبقى الأزواج كوحدات ثنائية.", "Pasangan tetap dihitung berpasangan."],
    ["Singles and doubles.", "Individuales y dobles.", "Simple et double.", "الفردي والزوجي.", "Tunggal dan ganda."],
    ["On the field first.", "Primero, jugar en el campo.", "D’abord, jouer sur le terrain.", "أولًا المشاركة في الملعب.", "Utamakan yang bermain di lapangan."],
    ["Official ID first.", "Primero, identificación oficial.", "D’abord, l’identifiant officiel.", "ابدأ بالمعرّف الرسمي.", "Utamakan ID resmi."],
    ["Appearances first.", "Primero, las participaciones.", "D’abord, les apparitions.", "ابدأ بالمشاركات.", "Utamakan penampilan."],
    ["A snap-defined season cohort.", "Un grupo definido por jugadas registradas.", "Une cohorte définie par les actions enregistrées.", "مجموعة موسم تحددها اللعبات المسجلة.", "Kelompok musim berdasarkan snap tercatat."],
    ["Aggregate exact club contributions.", "Sumar las aportaciones exactas por club.", "Additionner les contributions exactes par club.", "اجمع مساهمات كل نادٍ الدقيقة.", "Gabungkan kontribusi tepat tiap klub."],
    ["Deduplicate athletes across events.", "Evitar duplicar atletas entre pruebas.", "Éliminer les doublons d’athlètes entre épreuves.", "أزل تكرار الرياضيين بين الفعاليات.", "Hapus duplikasi atlet antar nomor."],
    ["Every UFC bout in 2025.", "Cada combate UFC de 2025.", "Tous les combats UFC de 2025.", "كل نزال UFC في 2025.", "Setiap duel UFC pada 2025."],
    ["Every completed lap.", "Cada vuelta completada.", "Chaque tour terminé.", "كل لفة مكتملة.", "Setiap putaran selesai."],
    ["Every racing lap.", "Cada vuelta de carrera.", "Chaque tour de course.", "كل لفة سباق.", "Setiap putaran balap."],
    ["Every event start.", "Cada salida en una prueba.", "Chaque départ d’épreuve.", "كل انطلاقة في فعالية.", "Setiap start nomor."],
    ["Every fight.", "Cada combate.", "Chaque combat.", "كل نزال.", "Setiap duel."],
    ["Every set played.", "Cada set jugado.", "Chaque set joué.", "كل شوط لُعب.", "Setiap set dimainkan."],
    ["One appearance.", "Una participación.", "Une apparition.", "مشاركة واحدة.", "Satu penampilan."],
    ["One athlete.", "Un atleta.", "Un athlète.", "رياضي واحد.", "Satu atlet."],
    ["One bout.", "Un combate.", "Un combat.", "نزال واحد.", "Satu duel."],
    ["One court entry.", "Una entrada en pista.", "Une entrée sur le terrain.", "دخول واحد إلى الملعب.", "Satu kali masuk lapangan."],
    ["One entry per event.", "Una inscripción por prueba.", "Une participation par épreuve.", "مشاركة واحدة لكل فعالية.", "Satu keikutsertaan per nomor."],
    ["One match.", "Un partido.", "Un match.", "مباراة واحدة.", "Satu pertandingan."],
    ["One start.", "Una salida.", "Un départ.", "انطلاقة واحدة.", "Satu start."],
    ["Two appearances.", "Dos participaciones.", "Deux apparitions.", "مشاركتان.", "Dua penampilan."],
    ["Two games.", "Dos partidos.", "Deux matchs.", "مباراتان.", "Dua pertandingan."],
    ["Two leagues", "Dos ligas", "Deux championnats", "دوريان", "Dua liga"],
    ["Two conferences", "Dos conferencias", "Deux conférences", "مؤتمران", "Dua konferensi"],
    ["All five BWF disciplines.", "Las cinco modalidades BWF.", "Les cinq disciplines BWF.", "جميع تخصصات BWF الخمسة.", "Kelima disiplin BWF."],
    ["All 49 events at Tokyo 2025.", "Las 49 pruebas de Tokio 2025.", "Les 49 épreuves de Tokyo 2025.", "جميع فعاليات طوكيو 2025 الـ49.", "Seluruh 49 nomor Tokyo 2025."],
    ["Five championships. One map.", "Cinco campeonatos. Un mapa.", "Cinq championnats. Une carte.", "خمس بطولات. خريطة واحدة.", "Lima kejuaraan. Satu peta."],
    ["Four routes up the grid", "Cuatro caminos hacia la parrilla", "Quatre voies vers la grille", "أربعة مسارات إلى شبكة الانطلاق", "Empat jalur menuju grid"],
    ["Points are not compared between series", "Los puntos no se comparan entre categorías", "Les points ne sont pas comparés entre séries", "لا تُقارن النقاط بين الفئات", "Poin tidak dibandingkan antar seri"],
    ["Relay-only athletes remain visible", "Los atletas solo de relevos siguen visibles", "Les athlètes de relais uniquement restent visibles", "يبقى رياضيو التتابع فقط ظاهرين", "Atlet yang hanya ikut estafet tetap ditampilkan"],
    ["Choose up to 6", "Elige hasta 6", "Choisissez jusqu’à 6", "اختر حتى 6", "Pilih hingga 6"],
    ["Choose up to six teams", "Elige hasta seis equipos", "Choisissez jusqu’à six équipes", "اختر حتى ستة فرق", "Pilih hingga enam tim"],
    ["Player-matches", "Partidos por jugador", "Matchs par joueur", "مباريات اللاعبين", "Pertandingan pemain"],
    ["Events played", "Pruebas disputadas", "Épreuves disputées", "الفعاليات التي لُعبت", "Nomor yang diikuti"],
    ["FIP profiles", "Perfiles FIP", "Profils FIP", "ملفات FIP", "Profil FIP"],
    ["Final 2025 top 100", "Top 100 final de 2025", "Top 100 final de 2025", "أفضل 100 في التصنيف النهائي لعام 2025", "100 besar akhir 2025"],
    ["2025 calendar year", "Año natural 2025", "Année civile 2025", "السنة التقويمية 2025", "Tahun kalender 2025"],
    ["2025 home-and-away season", "Temporada regular 2025", "Saison régulière 2025", "الموسم الاعتيادي 2025", "Musim kandang dan tandang 2025"],
    ["2025 year-end ranking", "Clasificación final de 2025", "Classement de fin d’année 2025", "تصنيف نهاية 2025", "Peringkat akhir tahun 2025"],
    ["2025 year-end top 100", "Top 100 final de 2025", "Top 100 de fin d’année 2025", "أفضل 100 لنهاية 2025", "100 besar akhir tahun 2025"],
    ["2025 year-end totals", "Totales finales de 2025", "Totaux de fin d’année 2025", "مجاميع نهاية 2025", "Total akhir tahun 2025"],
    ["Keep 100 players from each division.", "Conservar 100 jugadores por división.", "Garder 100 joueurs par division.", "احتفظ بـ100 لاعب من كل فئة.", "Pertahankan 100 pemain dari tiap divisi."],
    ["Keep 2025 home-and-away player rows.", "Conservar los registros de jugadores de la temporada regular 2025.", "Garder les lignes de joueurs de la saison régulière 2025.", "احتفظ بسجلات لاعبي الموسم الاعتيادي 2025.", "Pertahankan data pemain musim kandang dan tandang 2025."],
    ["Keep all 42 UFC cards in calendar 2025.", "Conservar las 42 carteleras UFC de 2025.", "Garder les 42 cartes UFC de l’année civile 2025.", "احتفظ بجميع بطاقات UFC الـ42 في 2025.", "Pertahankan seluruh 42 kartu UFC sepanjang 2025."],
    ["Keep exact ranks 1–100 from each tour.", "Conservar los puestos exactos 1–100 de cada circuito.", "Garder les rangs exacts de 1 à 100 de chaque circuit.", "احتفظ بالمراتب الدقيقة من 1 إلى 100 لكل جولة.", "Pertahankan peringkat tepat 1–100 dari tiap tur."],
    ["Keep exact ranks 1–100 per ranking.", "Conservar los puestos exactos 1–100 de cada clasificación.", "Garder les rangs exacts de 1 à 100 de chaque classement.", "احتفظ بالمراتب الدقيقة من 1 إلى 100 لكل تصنيف.", "Pertahankan peringkat tepat 1–100 dari tiap daftar."],
    ["Keep unresolved identities visible.", "Mantener visibles las identidades sin resolver.", "Garder visibles les identités non résolues.", "أبقِ الهويات غير المحسومة ظاهرة.", "Tampilkan identitas yang belum dipastikan."],
    ["Keep unresolved players visible in QA.", "Mantener visibles para revisión a los jugadores sin resolver.", "Garder visibles les joueurs non résolus pour vérification.", "أبقِ اللاعبين غير المحسومين ظاهرين للمراجعة.", "Tampilkan pemain yang belum dipastikan dalam pemeriksaan."],
    ["Match the NBA.com player ID in Wikidata.", "Cotejar el ID de jugador de NBA.com en Wikidata.", "Faire correspondre l’identifiant NBA.com du joueur dans Wikidata.", "طابق معرّف لاعب NBA.com في Wikidata.", "Cocokkan ID pemain NBA.com di Wikidata."],
    ["Preserve each system’s raw point values.", "Conservar los puntos originales de cada sistema.", "Préserver les points bruts de chaque système.", "احتفظ بقيم النقاط الأصلية لكل نظام.", "Pertahankan nilai poin mentah tiap sistem."],
    ["Preserve exact club contributions.", "Conservar las aportaciones exactas de cada club.", "Préserver les contributions exactes de chaque club.", "احتفظ بمساهمات كل نادٍ الدقيقة.", "Pertahankan kontribusi tepat tiap klub."],
    ["Preserve raw FIP ranking points.", "Conservar los puntos FIP originales.", "Préserver les points FIP bruts.", "احتفظ بنقاط تصنيف FIP الأصلية.", "Pertahankan poin peringkat FIP mentah."],
    ["Publish non-city birthplaces to QA.", "Enviar a revisión los nacimientos fuera de ciudades.", "Soumettre à vérification les naissances hors ville.", "أحِل أماكن الميلاد غير المحددة بمدينة للمراجعة.", "Kirim tempat lahir nonkota untuk pemeriksaan."],
    ["Read all 204 completed match files.", "Leer los 204 archivos de partidos terminados.", "Lire les 204 fichiers de matchs terminés.", "اقرأ ملفات المباريات المكتملة الـ204.", "Baca seluruh 204 berkas pertandingan selesai."],
    ["Use named relay lineups from each round.", "Usar las alineaciones nominales de relevos de cada ronda.", "Utiliser les compositions nominatives des relais de chaque tour.", "استخدم تشكيلات التتابع المسماة في كل جولة.", "Gunakan susunan estafet bernama dari tiap babak."],
    ["Two completed 2025 VNL competitions.", "Dos competiciones VNL completas de 2025.", "Deux compétitions VNL 2025 terminées.", "بطولتا VNL مكتملتان في 2025.", "Dua kompetisi VNL 2025 yang selesai."],
    ["Two official year-end rankings.", "Dos clasificaciones oficiales de fin de año.", "Deux classements officiels de fin d’année.", "تصنيفان رسميان لنهاية العام.", "Dua peringkat resmi akhir tahun."],
    ["Two official completed-season snapshots.", "Dos resúmenes oficiales de temporada completa.", "Deux aperçus officiels de saisons terminées.", "لمحتان رسميتان لموسمين مكتملين.", "Dua ringkasan resmi musim selesai."],
    ["Four completed 2025 championships.", "Cuatro campeonatos completos de 2025.", "Quatre championnats 2025 terminés.", "أربع بطولات مكتملة في 2025.", "Empat kejuaraan 2025 yang selesai."],
    ["Five completed 2025 championships.", "Cinco campeonatos completos de 2025.", "Cinq championnats 2025 terminés.", "خمس بطولات مكتملة في 2025.", "Lima kejuaraan 2025 yang selesai."],
    ["big leagues come from.", "jugadores de las grandes ligas.", "joueurs des grands championnats.", "لاعبو الدوريات الكبرى.", "pemain liga besar."],
    ["top 200 come from.", "mejores 200.", "200 meilleurs.", "أفضل 200.", "200 besar."],
    ["top golfers come from.", "mejores golfistas.", "meilleurs golfeurs.", "أفضل لاعبي الغولف.", "pegolf teratas."],
    ["AFL comes from.", "del AFL.", "de l’AFL.", "لاعبو AFL.", "AFL."],
    ["NBA comes from.", "de la NBA.", "de la NBA.", "لاعبو NBA.", "NBA."],
    ["NHL comes from.", "de la NHL.", "de la NHL.", "لاعبو NHL.", "NHL."],
    ["NRL comes from.", "de la NRL.", "de la NRL.", "لاعبو NRL.", "NRL."],
    ["NFL is built.", "de la NFL.", "de la NFL.", "لاعبو NFL.", "NFL."],
    ["allocated ranking points", "puntos de clasificación asignados", "points de classement attribués", "نقاط التصنيف المخصصة", "poin peringkat dialokasikan"],
    ["completed championship laps", "vueltas de campeonato completadas", "tours de championnat terminés", "لفات البطولة المكتملة", "putaran kejuaraan selesai"],
    ["fighter appearances", "participaciones de luchadores", "apparitions de combattants", "مشاركات المقاتلين", "penampilan petarung"],
    ["offense + defense + special teams", "ataque + defensa + equipos especiales", "attaque + défense + unités spéciales", "الهجوم + الدفاع + الفرق الخاصة", "serangan + pertahanan + tim khusus"],
    ["one per player per match", "uno por jugador y partido", "un par joueur et par match", "واحد لكل لاعب في كل مباراة", "satu per pemain per pertandingan"],
    ["pair points split equally", "puntos repartidos por igual entre la pareja", "points partagés également entre partenaires", "النقاط موزعة بالتساوي بين الشريكين", "poin pasangan dibagi rata"],
    ["plate appearances + batters faced", "turnos de bateo + bateadores enfrentados", "passages au bâton + frappeurs affrontés", "مرات الضرب + الضاربون المواجَهون", "giliran memukul + pemukul yang dihadapi"],
    ["sets played on court", "sets jugados en pista", "sets joués sur le terrain", "الأشواط الملعوبة في الملعب", "set dimainkan di lapangan"],
    ["unique athlete-event starts", "salidas únicas de atletas por prueba", "départs uniques d’athlètes par épreuve", "انطلاقات رياضيين فريدة لكل فعالية", "start unik atlet per nomor"],
    ["unique in the current selection", "únicos en la selección actual", "uniques dans la sélection actuelle", "فريدون في الاختيار الحالي", "unik dalam pilihan saat ini"],
    ["unique in this selection", "únicos en esta selección", "uniques dans cette sélection", "فريدون في هذا الاختيار", "unik dalam pilihan ini"],
    ["within separate systems", "dentro de sistemas separados", "dans des systèmes distincts", "ضمن أنظمة منفصلة", "dalam sistem terpisah"],
    ["editions", "ediciones", "éditions", "نسخ", "edisi"],
    ["federations", "federaciones", "fédérations", "اتحادات", "federasi"],
    ["rankings", "clasificaciones", "classements", "تصنيفات", "peringkat"],
    ["tours", "circuitos", "circuits", "جولات", "tur"],
    ["event entries", "inscripciones en pruebas", "participations aux épreuves", "مشاركات في الفعاليات", "keikutsertaan nomor"],
    ["birthplaces", "lugares de nacimiento", "lieux de naissance", "أماكن الميلاد", "tempat lahir"],
    ["total", "total", "total", "الإجمالي", "total"],
    ["Reset", "Restablecer", "Réinitialiser", "إعادة ضبط", "Atur ulang"],
    ["Geo", "Geografía", "Géo", "الجغرافيا", "Geo"],
    ["Talent", "Talento", "Talent", "المواهب", "Talenta"],
    ["Entries", "Inscripciones", "Participations", "المشاركات", "Keikutsertaan"],
    ["Event entries", "Inscripciones en pruebas", "Participations aux épreuves", "المشاركات في الفعاليات", "Keikutsertaan nomor"],
    ["Medals", "Medallas", "Médailles", "الميداليات", "Medali"],
    ["Gold", "Oro", "Or", "ذهبية", "Emas"],
    ["Silver", "Plata", "Argent", "فضية", "Perak"],
    ["Races", "Carreras", "Courses", "السباقات", "Balapan"],
    ["Rounds", "Rondas", "Tours", "الجولات", "Babak"],
    ["Federation", "Federación", "Fédération", "الاتحاد", "Federasi"],
    ["Group", "Grupo", "Groupe", "المجموعة", "Grup"],
    ["Tour group", "Grupo de circuitos", "Groupe de circuits", "مجموعة الجولات", "Grup tur"],
    ["Ranking group", "Grupo de clasificaciones", "Groupe de classements", "مجموعة التصنيفات", "Grup peringkat"],
    ["Division group", "Grupo de divisiones", "Groupe de divisions", "مجموعة الفئات", "Grup divisi"],
    ["Position", "Posición", "Position", "المركز", "Posisi"],
    ["Gender comparison", "Comparación por género", "Comparaison par genre", "مقارنة حسب الجنس", "Perbandingan gender"],
    ["Competition comparison", "Comparación de competiciones", "Comparaison des compétitions", "مقارنة المنافسات", "Perbandingan kompetisi"],
    ["Series comparison", "Comparación de categorías", "Comparaison des séries", "مقارنة الفئات", "Perbandingan seri"],
    ["Conferences, teams & generations", "Conferencias, equipos y generaciones", "Conférences, équipes et générations", "المؤتمرات والفرق والأجيال", "Konferensi, tim & generasi"],
    ["Conferences, teams & player mix", "Conferencias, equipos y composición de jugadores", "Conférences, équipes et composition des joueurs", "المؤتمرات والفرق وتنوع اللاعبين", "Konferensi, tim & komposisi pemain"],
    ["Leagues, teams & generations", "Ligas, equipos y generaciones", "Championnats, équipes et générations", "الدوريات والفرق والأجيال", "Liga, tim & generasi"],
    ["League, clubs & generations", "Liga, clubes y generaciones", "Championnat, clubs et générations", "الدوري والأندية والأجيال", "Liga, klub & generasi"],
    ["Divisions & generations", "Divisiones y generaciones", "Divisions et générations", "الفئات والأجيال", "Divisi & generasi"],
    ["Disciplines & generations", "Disciplinas y generaciones", "Disciplines et générations", "التخصصات والأجيال", "Disiplin & generasi"],
    ["Rankings & generations", "Clasificaciones y generaciones", "Classements et générations", "التصنيفات والأجيال", "Peringkat & generasi"],
    ["Tours & generations", "Circuitos y generaciones", "Circuits et générations", "الجولات والأجيال", "Tur & generasi"],
    ["Teams & competitions", "Equipos y competiciones", "Équipes et compétitions", "الفرق والمنافسات", "Tim & kompetisi"],
    ["Series & teams", "Categorías y equipos", "Séries et équipes", "الفئات والفرق", "Seri & tim"],
    ["Competitions & federations", "Competiciones y federaciones", "Compétitions et fédérations", "المنافسات والاتحادات", "Kompetisi & federasi"],
    ["Gender & teams", "Género y equipos", "Genre et équipes", "الجنس والفرق", "Gender & tim"],
    ["Gender & weight classes", "Género y categorías de peso", "Genre et catégories de poids", "الجنس وفئات الوزن", "Gender & kelas berat"],
    ["Geographic footprint", "Alcance geográfico", "Empreinte géographique", "الانتشار الجغرافي", "Jangkauan geografis"],
    ["Known location", "Ubicación conocida", "Lieu connu", "موقع معروف", "Lokasi diketahui"],
    ["Location country", "País de ubicación", "Pays du lieu", "بلد الموقع", "Negara lokasi"],
    ["Location lens", "Perspectiva de ubicación", "Vue des lieux", "منظور الموقع", "Sudut pandang lokasi"],
    ["Both leagues", "Ambas ligas", "Les deux championnats", "كلا الدوريين", "Kedua liga"],
    ["All groups", "Todos los grupos", "Tous les groupes", "جميع المجموعات", "Semua grup"],
    ["All federations", "Todas las federaciones", "Toutes les fédérations", "جميع الاتحادات", "Semua federasi"],
    ["All location countries", "Todos los países de ubicación", "Tous les pays des lieux", "جميع بلدان المواقع", "Semua negara lokasi"],
    ["All eight divisions", "Las ocho divisiones", "Les huit divisions", "جميع الفئات الثماني", "Kedelapan divisi"],
    ["Men", "Hombres", "Hommes", "الرجال", "Putra"],
    ["Women", "Mujeres", "Femmes", "النساء", "Putri"],
    ["Doubles", "Dobles", "Double", "الزوجي", "Ganda"],
    ["Singles", "Individuales", "Simple", "الفردي", "Tunggal"],
    ["Offense", "Ataque", "Attaque", "الهجوم", "Serangan"],
    ["Defense", "Defensa", "Défense", "الدفاع", "Pertahanan"],
    ["Special", "Equipos especiales", "Unités spéciales", "الفرق الخاصة", "Tim khusus"],
    ["Playing time", "Tiempo de juego", "Temps de jeu", "وقت اللعب", "Waktu bermain"],
    ["Sets played", "Sets jugados", "Sets joués", "الأشواط الملعوبة", "Set dimainkan"],
    ["Ranked entries", "Participantes clasificados", "Participants classés", "المشاركات المصنفة", "Peserta berperingkat"],
    ["Allocated points", "Puntos asignados", "Points attribués", "النقاط المخصصة", "Poin dialokasikan"],
    ["Total points", "Puntos totales", "Total des points", "إجمالي النقاط", "Total poin"],
    ["Average points", "Puntos medios", "Points moyens", "متوسط النقاط", "Rata-rata poin"],
    ["Best rank", "Mejor posición", "Meilleur rang", "أفضل تصنيف", "Peringkat terbaik"],
    ["Year-end birthplace map", "Mapa de nacimientos de fin de año", "Carte des naissances de fin d’année", "خريطة أماكن الميلاد لنهاية العام", "Peta tempat lahir akhir tahun"],
    ["Top-100 birthplace map", "Mapa de nacimientos del top 100", "Carte des naissances du top 100", "خريطة أماكن ميلاد أفضل 100", "Peta tempat lahir 100 besar"],
    ["World top-100 birthplace map", "Mapa de nacimientos del top 100 mundial", "Carte des naissances du top 100 mondial", "خريطة أماكن ميلاد أفضل 100 عالميًا", "Peta tempat lahir 100 besar dunia"],
    ["Read comparisons carefully", "Lee las comparaciones con cuidado", "Lisez les comparaisons avec prudence", "اقرأ المقارنات بحذر", "Baca perbandingan dengan cermat"],
  ]);

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
  const sourceTitle = document.title;
  let language = "en";
  try {
    const saved = localStorage.getItem("talent-geo-language") || localStorage.getItem("football-geo-language");
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
    if ((match = source.match(/^([^:]+): (.+)$/)) && dictionary.has(match[1])) return `${word(match[1])}: ${translateCore(match[2])}`;
    if ((match = source.match(/^Interactive (.+) map$/))) return `${{es:"Mapa interactivo",fr:"Carte interactive",ar:"خريطة تفاعلية",id:"Peta interaktif"}[language]} · ${translateCore(match[1])}`;
    if ((match = source.match(/^Search (.+)$/))) return `${{es:"Buscar",fr:"Chercher",ar:"ابحث عن",id:"Cari"}[language]} ${translateCore(match[1])}`;
    if ((match = source.match(/^Try (.+)$/))) return `${{es:"Prueba",fr:"Essayez",ar:"جرّب",id:"Coba"}[language]} ${match[1]}`;
    if ((match = source.match(/^Open (.+) source ↗$/))) return `${{es:"Abrir fuente de",fr:"Ouvrir la source de",ar:"افتح مصدر",id:"Buka sumber"}[language]} ${match[1]} ↗`;
    if ((match = source.match(/^Open (.+) ↗$/))) return `${{es:"Abrir",fr:"Ouvrir",ar:"افتح",id:"Buka"}[language]} ${translateCore(match[1])} ↗`;
    if ((match = source.match(/^Loading (.+)…$/))) return `${{es:"Cargando",fr:"Chargement de",ar:"جارٍ تحميل",id:"Memuat"}[language]} ${translateCore(match[1])}…`;
    if ((match = source.match(/^All (\d+) teams$/))) return ({es:`Los ${match[1]} equipos`,fr:`Les ${match[1]} équipes`,ar:`جميع الفرق الـ${match[1]}`,id:`Semua ${match[1]} tim`})[language];
    if ((match = source.match(/^([\d.,]+) ([a-z][a-z -]+)$/)) && dictionary.has(match[2])) return `${match[1]} ${word(match[2])}`;
    if ((match = source.match(/^Compare (.+)$/))) return `${word("Compare")} ${translateCore(match[1])}`;
    if ((match = source.match(/^Current (.+) selection summary$/))) return `${word("Current selection summary")} · ${translateCore(match[1])}`;
    if ((match = source.match(/^(.+) players matching (?:the current )?filters$/))) return `${word("Players")} ${translateCore(match[1])} ${{es:"que coinciden con los filtros",fr:"correspondant aux filtres",ar:"المطابقون للمرشحات",id:"yang sesuai filter"}[language]}`;
    if ((match = source.match(/^(.+) matching (?:the current )?filters$/))) return `${translateCore(match[1])} · ${{es:"coinciden con los filtros",fr:"correspondent aux filtres",ar:"يطابقون المرشحات",id:"sesuai filter"}[language]}`;
    if ((match = source.match(/^(.+) birthplace map$/))) return `${word("Birthplace")} · ${translateCore(match[1])} ${word("Map view")}`;
    if ((match = source.match(/^([\d.,]+) ([A-Za-z][A-Za-z -]+)$/)) && dictionary.has(match[2])) return `${match[1]} ${word(match[2])}`;
    if ((match = source.match(/^(.+) in selection$/))) return `${translateCore(match[1])} ${word("in the current selection")}`;
    if ((match = source.match(/^— mapped (.+)$/))) return `— ${word("mapped")} ${translateCore(match[1])}`;
    if ((match = source.match(/^— (.+)$/))) return `— ${translateCore(match[1])}`;
    if ((match = source.match(/^Birthplace mix, player age and team (.+)$/))) return `${{es:"Orígenes, edades y",fr:"Origines, âges et",ar:"أماكن الميلاد والأعمار و",id:"Tempat lahir, usia, dan"}[language]} ${translateCore(match[1])}`;
    if ((match = source.match(/^(.+) Talent Geography home$/))) return `${translateCore(match[1])} · ${{es:"inicio",fr:"accueil",ar:"الصفحة الرئيسية",id:"beranda"}[language]}`;
    if ((match = source.match(/^(.+) Talent Geography$/))) return `${translateCore(match[1])} · ${word("Talent Geography")}`;
    if ((match = source.match(/^(.+) dashboard (filters|views)$/))) return `${word(match[2] === "filters" ? "Dashboard filters" : "Dashboard views")} · ${translateCore(match[1])}`;
    if ((match = source.match(/^Close (player|driver|rider|fighter|athlete|golfer) profile$/))) return `${{es:"Cerrar perfil",fr:"Fermer le profil",ar:"إغلاق ملف",id:"Tutup profil"}[language]} ${word(match[1][0].toUpperCase() + match[1].slice(1))}`;
    if ((match = source.match(/^([\w\s-]+) profile$/))) return `${word("Player profile")} · ${translateCore(match[1])}`;
    if ((match = source.match(/^Building the (.+) map$/))) return `${{es:"Preparando el mapa",fr:"Préparation de la carte",ar:"جارٍ إعداد الخريطة",id:"Menyiapkan peta"}[language]} · ${translateCore(match[1])}`;
    if ((match = source.match(/^([\w\s-]+) per 1M$/))) return `${translateCore(match[1])} ${word("per 1M")}`;
    if ((match = source.match(/^([\w\s-]+) coverage$/))) return `${word("Coverage")} · ${translateCore(match[1])}`;
    if ((match = source.match(/^([\w\s-]+)-level detail$/))) return `${{es:"Detalle de",fr:"Détail des",ar:"تفاصيل",id:"Detail"}[language]} ${translateCore(match[1])}`;
    if ((match = source.match(/^Unresolved ([\w\s-]+)$/))) return `${word("unresolved")} ${translateCore(match[1])}`;
    if ((match = source.match(/^Show more ([\w\s-]+)$/))) return `${{es:"Mostrar más",fr:"Afficher plus de",ar:"عرض المزيد من",id:"Tampilkan lebih banyak"}[language]} ${translateCore(match[1])}`;
    if ((match = source.match(/^Find (?:a |an )?(.+)$/))) return `${{es:"Buscar",fr:"Chercher",ar:"ابحث عن",id:"Cari"}[language]} ${translateCore(match[1])}`;
    if ((match = source.match(/^([\d.,\s—]+) (players|clubs|leagues|places|countries|areas|starts|mapped starts|mapped|unresolved|total|residents|starters|birthplaces|locations|teams|divisions|drivers|riders|fighters|athletes|golfers|cricketers|games|matches|appearances|laps|sets|bouts|snaps|points|wins|podiums|fights|ranking points|minutes)$/))) return `${match[1]} ${word(match[2])}`;
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
    document.title = translate(sourceTitle);
    const select = document.querySelector("#site-language");
    if (select) select.value = language;
    renderSubtree(document.body);
  }

  function setLanguage(next) {
    if (!codes.includes(next)) return;
    language = next;
    try { localStorage.setItem("talent-geo-language", language); } catch (_) { /* Storage can be disabled. */ }
    applyLanguage();
    document.dispatchEvent(new CustomEvent("footballlanguagechange", { detail: { language } }));
    document.dispatchEvent(new CustomEvent("talentgeolanguagechange", { detail: { language } }));
  }

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === "characterData") renderText(mutation.target);
      else if (mutation.type === "attributes") renderAttributes(mutation.target);
      else for (const node of mutation.addedNodes) renderSubtree(node);
    }
  });

  if (!document.querySelector("#site-language")) {
    document.querySelector(".site-header .sport-switcher")?.insertAdjacentHTML("afterend", '<label class="language-control" for="site-language"><span>Language</span><select id="site-language" aria-label="Language"><option value="en">English</option><option value="es">Español</option><option value="fr">Français</option><option value="ar">العربية</option><option value="id">Bahasa Indonesia</option></select></label>');
  }
  window.TalentGeoLanguage = window.FootballLanguage = { get language() { return language; }, get locale() { return locales[language]; }, setLanguage, translate };
  applyLanguage();
  document.querySelector("#site-language")?.addEventListener("change", (event) => setLanguage(event.target.value));
  observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: attributes });
})();
