.PHONY: release

release:
	git tag -fa v1 -m "v1"
	git push origin main
	git push origin v1 --force
