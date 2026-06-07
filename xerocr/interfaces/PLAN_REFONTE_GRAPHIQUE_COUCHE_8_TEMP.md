# Plan temporaire de refonte graphique - couche 8

Ce fichier est un aide-memoire de chantier. Il doit etre supprime une fois la
refonte terminee.

## Objectif

Amener l'interface XerOCR au niveau de qualite graphique de Picarones sans
perdre les fonctionnalites ajoutees depuis : bibliotheque locale, imports IIIF /
Gallica / eScriptorium / HuggingFace, benchmark, rapports, historique,
segmentation et etat des moteurs.

Le principe directeur est strict : ne pas empiler des couches successives de
refonte. Si un element ne sert plus, il est supprime. S'il sert encore, il est
modifie en place. S'il peut devenir commun, il est consolide une seule fois.

## Phases

### 1. Socle typographique

Statut : termine.

- Titres : Mona Sans VF, graisse forte.
- Corps et controles : IBM Plex Sans.
- Donnees et metadonnees : IBM Plex Mono.
- Accents editoriaux ponctuels : Fluxisch Else.
- Marque et tags tres courts : OCR-A.
- Les trois surfaces sont alignees : app web, design de reference, rapports
  autonomes.
- Les fontes sont auto-hebergees et packagees.

### 2. Systeme graphique de base

Statut : termine.

Objectif : rendre `shell.css` lisible et coherent sans creer de nouvelle feuille
parallele.

Actions realisees :

- Organiser la feuille en blocs stables : fonts, tokens, reset, shell,
  primitives, composants communs, vues.
- Consolider les composants communs deja presents : boutons, champs, select,
  tabs, sections, badges, etats vides, tables, cartes.
- Supprimer les variantes mortes ou redondantes au lieu de les garder comme
  compatibilite implicite.
- Garder les noms existants quand ils sont deja utilises par les templates ou le
  JavaScript.
- Eviter toute classe nouvelle si une classe existante peut etre clarifiee.

Critere de sortie :

- `shell.css` porte un vocabulaire graphique unique.
- Les templates existants n'ont pas besoin de shims.
- Library, Reports, Benchmark, History, Engines et Segmentation continuent de
  rendre et de passer les tests.

### 3. Library comme page pilote

Statut : termine.

Objectif : faire de Library la premiere page au niveau Picarones.

Actions realisees :

- Clarifier la hierarchie : hero, corpus locaux, sources distantes, recherche,
  resultats.
- Rendre l'import progressif : source choisie, champs pertinents visibles,
  actions lisibles.
- Conserver toutes les fonctionnalites d'import existantes.
- Verifier mobile et desktop.

Critere de sortie :

- La page Library ressemble a une vraie interface produit, pas a un formulaire
  long pose dans une carte.
- Aucun controle fonctionnel existant n'a disparu.

### 4. Pages operationnelles

Statut : termine.

Objectif : appliquer le meme systeme a Benchmark, Reports, History, Engines et
Segmentation.

Actions realisees :

- Reprendre les memes primitives : sections, tables, listes, etats, formulaires.
- Adapter la densite a l'usage : Benchmark doit etre efficace, Reports et
  History doivent etre scannables, Engines doit etre informatif.
- Supprimer les styles devenus specifiques par accident.

Critere de sortie :

- Les pages partagent le meme langage visuel.
- Il n'y a pas de duplication de composants sous des noms differents.

### 5. Cohesion responsive et accessibilite

Statut : termine.

Objectif : eviter les ruptures visuelles et les textes qui debordent.

Actions realisees :

- Revoir les grilles et rails sous mobile/tablette/desktop.
- Stabiliser les tailles de boutons, chips, cartes, tableaux et zones de depot.
- Garder focus visible, contrastes et labels accessibles.

Critere de sortie :

- L'interface reste utilisable sur petit ecran.
- Les composants ne changent pas de taille de facon inattendue.

### 6. Verification visuelle page par page

Statut : en cours.

Objectif : verifier que chaque ecran est lisible et que les sections tiennent
visuellement en desktop et mobile.

Actions :

- Inspecter `Library`, `Benchmark`, `Reports`, `History`, `Engines` et
  `Segmentation` dans le navigateur local.
- Verifier les etats vides, les pages peuplees et les pages avec donnees longues.
- Chercher les debordements de texte, les alignements faibles et les panneaux
  qui respirent mal.

Actions realisees :

- Reference Picarones live verifiee depuis le Space HuggingFace et sa CSS
  d'application.
- XerOCR realigne sur les primitives visuelles utiles de Picarones : navigation
  en fenetre, hero avec groupe de statistiques, sections numerotees, corps de
  section explicite et etats vides communs.
- Benchmark, Library, Reports, History, Engines et Segmentation utilisent le
  meme contrat de section.

Blocage courant :

- Les captures navigateur locales restent a refaire des qu'un navigateur local
  pilotable est disponible dans la session.

Critere de sortie :

- Aucun ecran principal n'a de casse visuelle evidente.

### 7. Nettoyage CSS final

Statut : en cours.

Objectif : supprimer ce qui ne sert plus apres la refonte.

Actions :

- Chercher les classes CSS mortes et les supprimer.
- Chercher les doublons de tokens, composants ou formulations.
- Verifier qu'il ne reste pas de styles inline ou de variantes paralleles inutiles.

Actions realisees :

- Suppression des anciens fragments de presentation `muted`, `report-empty`,
  `field-sep`, `corpus-grid` et du wrapper `launcher` devenu inutile.
- Conservation des classes seulement si elles sont encore utilisees par les
  templates ou le JavaScript.
- Verification ciblee des pages web, syntaxe JS et whitespace du diff.

Critere de sortie :

- Le code final ne contient pas d'artefacts de couches successives.

### 8. Rapports autonomes et HuggingFace Space

Statut : a faire.

Objectif : verifier que les rapports HTML autonomes et le deploiement Space
restent coherents avec la nouvelle typographie et les assets embarques.

Actions :

- Verifier que les rapports rendent bien avec les fonts incorporees.
- Verifier que les chemins de fonts packagees sont corrects dans le wheel.
- Verifier que la presentation sur le Space HuggingFace reste stable.

Critere de sortie :

- Les rapports autonomes gardent leur autonomie et leur identite visuelle.

### 9. Verification packaging / assets

Statut : a faire.

Objectif : confirmer que les nouveaux assets graphiques voyagent bien partout
ou ils doivent voyager.

Actions :

- Verifier les `package-data` et les fichiers de polices ajoutes.
- Verifier que les assets web et rapports sont presents apres installation.
- Verifier que rien d'utile n'est reste hors du wheel.

Critere de sortie :

- L'application installee et le Space voient les memes assets attendus.

### 10. Tests finaux plus larges

Statut : a faire.

Objectif : valider le resultat sur la surface complete, pas seulement sur les
cas ciblés de mise au point.

Actions :

- Relancer la suite web complete.
- Verifier les tests de rapports et les checks JS.
- Refaire les parcours de lecture et de lancement de run.

Critere de sortie :

- La refonte est stable sur les chemins critiques.

### 11. Fermeture du chantier

Statut : a faire.

Objectif : nettoyer le chantier et rendre la refonte lisible dans le repo.

Actions :

- Supprimer ce fichier temporaire.
- Verifier qu'aucun commentaire ou reference de chantier ne reste utilement.
- Preparer le commit ou la suite du travail a partir de l'etat reel du code.

Critere de sortie :

- Aucun artefact temporaire ne reste dans le repo.
- Le code final correspond au systeme reel, pas a l'historique de la refonte.
